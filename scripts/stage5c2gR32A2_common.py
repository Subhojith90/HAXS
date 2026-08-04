from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
import uuid
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
STAGE = "stage5c2gR32A2"
CANDIDATE_PATH = ROOT / "results/stage5c2gR32A2/protocol/CANDIDATE.json"
ROOT_MANIFEST_PATH = ROOT / "results/stage5c2gR32A2/protocol/ROOT_MANIFEST.json"
LOCK_PATH = ROOT / "results/stage5c2gR32A2/protocol/LOCKED.json"
RECEIPT_PATH = ROOT / "results/stage5c2gR32A2/protocol/SUPERVISOR_AUTHORIZATION_G1_ONLY.json"
AUTHORIZATION_PATH = ROOT / "results/stage5c2gR32A2/protocol/AUTHORIZATION.json"
STATE_PATH = ROOT / "results/stage5c2gR32A2/state/G1.json"
SETUP_STATE_PATH = ROOT / "results/stage5c2gR32A2/preflight/SETUP.json"

FORBIDDEN_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
FORBIDDEN_SUFFIXES = {".pyc", ".pyo", ".pth"}
FORBIDDEN_ROOT_HOOKS = {"conftest.py", "sitecustomize.py", "usercustomize.py"}


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_payload(payload: object) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def strict_json(path: Path) -> dict:
    if not path.is_file() or path.is_symlink():
        raise RuntimeError(f"missing or unsafe JSON object: {path}")

    def exact_object(pairs: list[tuple[str, object]]) -> dict:
        payload: dict = {}
        for key, value in pairs:
            if key in payload:
                raise RuntimeError(f"duplicate JSON key: {key}")
            payload[key] = value
        return payload

    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=exact_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"invalid strict JSON: {path}") from error
    if not isinstance(value, dict):
        raise RuntimeError(f"expected a JSON object: {path}")
    return value


def safe_relative(value: str) -> Path:
    pure = PurePosixPath(value)
    if pure.is_absolute() or not pure.parts or ".." in pure.parts or "" in pure.parts:
        raise RuntimeError(f"unsafe relative path: {value!r}")
    return Path(*pure.parts)


def exclusive_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    try:
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH,
        )
    except FileExistsError as error:
        raise RuntimeError(f"refusing to overwrite exclusive object: {path}") from error
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    os.replace(temporary, path)


def load_candidate(root: Path = ROOT) -> dict:
    path = root / CANDIDATE_PATH.relative_to(ROOT)
    candidate = strict_json(path)
    canonical = {key: value for key, value in candidate.items() if key != "candidate_sha256"}
    if candidate.get("schema_version") != "haxs.stage5c2gR32A2.candidate.v1":
        raise RuntimeError("predecessor or unknown candidate schema rejected")
    if candidate.get("candidate_sha256") != sha256_payload(canonical):
        raise RuntimeError("R3.2A.2 candidate self-identity failed")
    return candidate


def verify_record(root: Path, record: dict, label: str) -> Path:
    if set(record) != {"path", "sha256"}:
        raise RuntimeError(f"{label} does not use the exact bound-record schema")
    path = root / safe_relative(str(record["path"]))
    if not path.is_file() or path.is_symlink() or sha256_file(path) != record["sha256"]:
        raise RuntimeError(f"candidate-bound object failed: {label}")
    return path


def tree_snapshot(root: Path) -> tuple[dict[str, str], list[str]]:
    if not root.is_dir() or root.is_symlink():
        raise RuntimeError("execution root is missing or is a symlink")
    files: dict[str, str] = {}
    directories: list[str] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise RuntimeError(f"symlink in execution root: {relative}")
        if path.is_dir():
            directories.append(relative)
        elif path.is_file():
            files[relative] = sha256_file(path)
        else:
            raise RuntimeError(f"unsupported filesystem object: {relative}")
    return files, directories


def assert_no_forbidden_import_artifacts(files: dict[str, str]) -> None:
    rejected = []
    for relative in files:
        path = PurePosixPath(relative)
        if FORBIDDEN_PARTS.intersection(path.parts) or path.suffix.lower() in FORBIDDEN_SUFFIXES:
            rejected.append(relative)
        if len(path.parts) == 1 and path.name in FORBIDDEN_ROOT_HOOKS:
            rejected.append(relative)
    if rejected:
        raise RuntimeError(f"forbidden bytecode/import artifacts: {sorted(set(rejected))[:8]}")


def assert_exact_membership(observed: dict[str, str], expected: dict[str, str], label: str = "root") -> None:
    if observed != expected:
        raise RuntimeError(
            f"{label} exact membership failed: "
            f"extra={sorted(set(observed)-set(expected))[:8]} "
            f"missing={sorted(set(expected)-set(observed))[:8]}"
        )


def reserve_attempt(candidate: dict, authorization: dict, root: Path = ROOT) -> dict:
    state_path = root / STATE_PATH.relative_to(ROOT)
    attempt_id = uuid.uuid4().hex
    artifact = root / "results/stage5c2gR32A2/artifacts" / candidate["candidate_sha256"] / "G1" / attempt_id
    running = {
        "schema_version": "haxs.stage5c2gR32A2.single-attempt-state.v1",
        "gate": "G1",
        "status": "RUNNING",
        "sequence": 1,
        "attempt_id": attempt_id,
        "candidate_sha256": candidate["candidate_sha256"],
        "receipt_id": authorization["receipt"]["receipt_id"],
        "artifact_path": artifact.relative_to(root).as_posix(),
        "error": "",
    }
    running["state_sha256"] = sha256_payload(running)
    exclusive_write_json(state_path, running)
    return running


def terminalize_attempt(running: dict, status: str, details: dict, root: Path = ROOT) -> dict:
    if status not in {"PASSED", "FAILED"}:
        raise ValueError("terminal state must be PASSED or FAILED")
    state_path = root / STATE_PATH.relative_to(ROOT)
    current = strict_json(state_path)
    canonical = {key: value for key, value in current.items() if key != "state_sha256"}
    if (
        current.get("status") != "RUNNING"
        or current.get("attempt_id") != running["attempt_id"]
        or current.get("state_sha256") != sha256_payload(canonical)
    ):
        raise RuntimeError("atomic G1 running state changed before terminalization")
    terminal = {**canonical, "status": status, **details}
    terminal["state_sha256"] = sha256_payload(terminal)
    atomic_write_json(state_path, terminal)
    return terminal
