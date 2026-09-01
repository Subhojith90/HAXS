from __future__ import annotations

import json
import os
import shutil
import uuid
from contextlib import contextmanager
from pathlib import Path

from stage5c2gR32A2_common import (
    atomic_write_json,
    exclusive_write_json,
    safe_relative,
    sha256_file,
    sha256_payload,
    strict_json,
)

ROOT = Path(__file__).resolve().parents[1]
STAGE = "stage5c2gR32A5"
CANDIDATE_PATH = ROOT / "results/stage5c2gR32A5/protocol/CANDIDATE.json"

RECEIPT_NAME = "SUPERVISOR_AUTHORIZATION_G1_ONLY.json"
AUTHORIZATION_NAME = "AUTHORIZATION.json"
SETUP_NAME = "SETUP.json"
STATE_NAME = "state/G1.json"


def load_candidate(root: Path = ROOT) -> dict:
    candidate = strict_json(root / CANDIDATE_PATH.relative_to(ROOT))
    canonical = {key: value for key, value in candidate.items() if key != "candidate_sha256"}
    if candidate.get("schema_version") != "haxs.stage5c2gR32A5.candidate.v1":
        raise RuntimeError("predecessor or unknown A5 candidate schema rejected")
    if candidate.get("candidate_sha256") != sha256_payload(canonical):
        raise RuntimeError("R3.2A.5 candidate self-identity failed")
    return candidate


def _assert_safe_ancestors(path: Path) -> None:
    current = path.absolute()
    while current != current.parent:
        if current.exists() and current.is_symlink():
            raise RuntimeError(f"control-root ancestor is symlinked: {current}")
        current = current.parent


def candidate_control_root(control_root: Path, candidate: dict, immutable_root: Path = ROOT) -> Path:
    base = control_root.absolute()
    immutable = immutable_root.resolve()
    _assert_safe_ancestors(base)
    try:
        base.resolve().relative_to(immutable)
    except ValueError:
        pass
    else:
        raise RuntimeError("mutable control root must be outside the immutable protocol root")
    candidate_sha = str(candidate.get("candidate_sha256", ""))
    if len(candidate_sha) != 64 or any(character not in "0123456789abcdef" for character in candidate_sha):
        raise RuntimeError("candidate namespace is not one lowercase SHA-256")
    return base / candidate_sha


def _files_and_directories(root: Path) -> tuple[dict[str, str], list[str]]:
    if root.is_symlink():
        raise RuntimeError("candidate control namespace is symlinked")
    files: dict[str, str] = {}
    directories: list[str] = []
    if not root.exists():
        return files, directories
    if not root.is_dir():
        raise RuntimeError("candidate control namespace is not a directory")
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise RuntimeError(f"control plane contains symlink: {relative}")
        if path.is_dir():
            directories.append(relative)
        elif path.is_file():
            files[relative] = sha256_file(path)
        else:
            raise RuntimeError(f"control plane contains unsupported object: {relative}")
    return files, directories


def _verify_self_hash(record: dict, field: str, label: str) -> None:
    canonical = {key: value for key, value in record.items() if key != field}
    if record.get(field) != sha256_payload(canonical):
        raise RuntimeError(f"{label} self-identity failed")


def verify_control_root(
    control_root: Path,
    candidate: dict,
    phase: str,
    immutable_root: Path = ROOT,
) -> dict:
    namespace = candidate_control_root(control_root, candidate, immutable_root)
    files, directories = _files_and_directories(namespace)
    expected = {RECEIPT_NAME, AUTHORIZATION_NAME}
    if phase in {"SETUP", "RUNNING", "TERMINAL"}:
        expected.add(SETUP_NAME)
    if phase in {"RUNNING", "TERMINAL"}:
        expected.add(STATE_NAME)
    if phase == "EMPTY":
        if files or directories or namespace.exists():
            raise RuntimeError("control namespace is not pristine")
        return {"stage": STAGE, "status": "PASS", "phase": phase, "files": 0}
    if phase not in {"AUTHORIZED", "SETUP", "RUNNING", "TERMINAL"}:
        raise ValueError("unknown control-plane phase")

    state = strict_json(namespace / STATE_NAME) if STATE_NAME in files else None
    if phase == "TERMINAL":
        if state is None or state.get("status") not in {"PASSED", "FAILED"}:
            raise RuntimeError("terminal control root lacks terminal state")
        attempt_id = state.get("attempt_id")
        artifact_base = f"artifacts/G1/{attempt_id}"
        expected.update({
            f"{artifact_base}/G1_EXECUTION_TRANSCRIPT.txt",
            f"{artifact_base}/ARTIFACT_MANIFEST.json",
        })
        manifest_path = namespace / artifact_base / "ARTIFACT_MANIFEST.json"
        if not manifest_path.is_file() or manifest_path.is_symlink():
            raise RuntimeError("terminal artifact manifest is missing or unsafe")
        manifest = strict_json(manifest_path)
        scientific_files = manifest.get("scientific_files")
        if not isinstance(scientific_files, dict):
            raise RuntimeError("terminal artifact manifest lacks scientific file closure")
        for relative, digest in scientific_files.items():
            safe = Path(relative)
            if (
                not relative or safe.is_absolute() or ".." in safe.parts
                or safe.as_posix() != relative or len(str(digest)) != 64
            ):
                raise RuntimeError("terminal scientific artifact path or digest is invalid")
            expected.add(f"{artifact_base}/scientific/{relative}")
    if set(files) != expected:
        raise RuntimeError(
            f"control-root exact membership failed: extra={sorted(set(files)-expected)} "
            f"missing={sorted(expected-set(files))}"
        )
    expected_directories = sorted({
        parent.as_posix()
        for name in expected
        for parent in Path(name).parents
        if parent != Path(".")
    })
    if sorted(directories) != expected_directories:
        raise RuntimeError("control-root exact directory membership failed")

    receipt = strict_json(namespace / RECEIPT_NAME)
    authorization = strict_json(namespace / AUTHORIZATION_NAME)
    _verify_self_hash(authorization, "authorization_sha256", "authorization")
    if (
        authorization.get("schema_version") != "haxs.stage5c2gR32A5.atomic-authorization.v1"
        or authorization.get("status") != "LOCKED_G1_ONLY"
        or authorization.get("candidate_sha256") != candidate["candidate_sha256"]
        or authorization.get("receipt_sha256") != sha256_file(namespace / RECEIPT_NAME)
        or authorization.get("receipt_id") != receipt.get("receipt_id")
        or authorization.get("official_attempt_limit") != 1
    ):
        raise RuntimeError("candidate-bound A5 authorization failed")
    if SETUP_NAME in files:
        setup = strict_json(namespace / SETUP_NAME)
        _verify_self_hash(setup, "setup_sha256", "setup")
        if setup.get("candidate_sha256") != candidate["candidate_sha256"] or setup.get("status") != "PASS":
            raise RuntimeError("candidate-bound setup record failed")
    if state is not None:
        _verify_self_hash(state, "state_sha256", "attempt state")
        if state.get("candidate_sha256") != candidate["candidate_sha256"]:
            raise RuntimeError("attempt state candidate mismatch")
        expected_status = "RUNNING" if phase == "RUNNING" else {"PASSED", "FAILED"}
        if isinstance(expected_status, str) and state.get("status") != expected_status:
            raise RuntimeError("attempt state phase mismatch")
        if isinstance(expected_status, set) and state.get("status") not in expected_status:
            raise RuntimeError("attempt terminal phase mismatch")
    if phase == "TERMINAL":
        artifact_base = namespace / "artifacts/G1" / state["attempt_id"]
        manifest = strict_json(artifact_base / "ARTIFACT_MANIFEST.json")
        _verify_self_hash(manifest, "manifest_sha256", "artifact manifest")
        transcript = artifact_base / "G1_EXECUTION_TRANSCRIPT.txt"
        observed_scientific = {
            path.relative_to(artifact_base / "scientific").as_posix(): sha256_file(path)
            for path in sorted((artifact_base / "scientific").rglob("*"))
            if path.is_file()
        } if (artifact_base / "scientific").is_dir() else {}
        if (
            manifest.get("candidate_sha256") != candidate["candidate_sha256"]
            or manifest.get("attempt_id") != state["attempt_id"]
            or manifest.get("transcript_sha256") != sha256_file(transcript)
            or manifest.get("scientific_files") != observed_scientific
        ):
            raise RuntimeError("terminal artifact manifest failed")
    return {
        "stage": STAGE,
        "status": "PASS",
        "phase": phase,
        "candidate_sha256": candidate["candidate_sha256"],
        "files": len(files),
        "control_tree_sha256": sha256_payload(files),
    }


@contextmanager
def control_writer_lock(control_root: Path, candidate: dict, immutable_root: Path = ROOT):
    namespace = candidate_control_root(control_root, candidate, immutable_root)
    namespace.parent.mkdir(parents=True, exist_ok=True)
    lock = namespace.parent / f".{candidate['candidate_sha256']}.writer.lock"
    try:
        lock.mkdir()
    except FileExistsError as error:
        raise RuntimeError("another control-plane writer is active") from error
    try:
        yield namespace
    finally:
        try:
            lock.rmdir()
        except FileNotFoundError:
            pass


def commit_authorization_bundle(
    control_root: Path,
    candidate: dict,
    receipt_path: Path,
    authorization: dict,
    immutable_root: Path = ROOT,
) -> Path:
    if not receipt_path.is_file() or receipt_path.is_symlink():
        raise RuntimeError("supervisor receipt is missing or unsafe")
    with control_writer_lock(control_root, candidate, immutable_root) as namespace:
        if namespace.exists() or namespace.is_symlink():
            raise RuntimeError("authorization namespace already exists")
        temporary = namespace.parent / f".{namespace.name}.staging.{uuid.uuid4().hex}"
        try:
            temporary.mkdir()
            shutil.copy2(receipt_path, temporary / RECEIPT_NAME)
            payload = dict(authorization)
            payload["receipt_sha256"] = sha256_file(temporary / RECEIPT_NAME)
            payload["authorization_sha256"] = sha256_payload(payload)
            exclusive_write_json(temporary / AUTHORIZATION_NAME, payload)
            os.replace(temporary, namespace)
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)
    verify_control_root(control_root, candidate, "AUTHORIZED", immutable_root)
    return namespace


def reserve_attempt(control_root: Path, candidate: dict, authorization: dict, immutable_root: Path = ROOT) -> dict:
    namespace = candidate_control_root(control_root, candidate, immutable_root)
    state_path = namespace / STATE_NAME
    attempt_id = uuid.uuid4().hex
    running = {
        "schema_version": "haxs.stage5c2gR32A5.single-attempt-state.v1",
        "gate": "G1",
        "status": "RUNNING",
        "sequence": 1,
        "attempt_id": attempt_id,
        "candidate_sha256": candidate["candidate_sha256"],
        "receipt_id": authorization["receipt_id"],
        "artifact_path": f"artifacts/G1/{attempt_id}",
        "error": "",
    }
    running["state_sha256"] = sha256_payload(running)
    exclusive_write_json(state_path, running)
    return running


def terminalize_attempt(
    control_root: Path,
    candidate: dict,
    running: dict,
    status: str,
    transcript_text: str,
    error: str = "",
    scientific_output: Path | None = None,
    immutable_root: Path = ROOT,
) -> dict:
    if status not in {"PASSED", "FAILED"}:
        raise ValueError("terminal state must be PASSED or FAILED")
    namespace = candidate_control_root(control_root, candidate, immutable_root)
    state_path = namespace / STATE_NAME
    current = strict_json(state_path)
    _verify_self_hash(current, "state_sha256", "running state")
    if current.get("status") != "RUNNING" or current.get("attempt_id") != running.get("attempt_id"):
        raise RuntimeError("running state changed before terminalization")
    artifact = namespace / current["artifact_path"]
    artifact.mkdir(parents=True, exist_ok=False)
    transcript = artifact / "G1_EXECUTION_TRANSCRIPT.txt"
    transcript.write_text(transcript_text, encoding="utf-8")
    scientific_files: dict[str, str] = {}
    if scientific_output is not None:
        source = scientific_output.absolute()
        if not source.is_dir() or source.is_symlink():
            raise RuntimeError("scientific output root is missing or unsafe")
        destination = artifact / "scientific"
        destination.mkdir()
        for path in sorted(source.rglob("*")):
            relative = path.relative_to(source)
            if (
                path.is_symlink() or "__pycache__" in relative.parts
                or path.suffix.lower() in {".pyc", ".pyo", ".pth"}
            ):
                raise RuntimeError(f"forbidden scientific artifact: {relative}")
            target = destination / relative
            if path.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            elif path.is_file():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
                scientific_files[relative.as_posix()] = sha256_file(target)
            else:
                raise RuntimeError(f"unsupported scientific artifact: {relative}")
        if not scientific_files:
            raise RuntimeError("scientific output root is empty")
    manifest = {
        "schema_version": "haxs.stage5c2gR32A5.artifact-manifest.v1",
        "candidate_sha256": candidate["candidate_sha256"],
        "attempt_id": current["attempt_id"],
        "transcript_sha256": sha256_file(transcript),
        "scientific_files": scientific_files,
    }
    manifest["manifest_sha256"] = sha256_payload(manifest)
    exclusive_write_json(artifact / "ARTIFACT_MANIFEST.json", manifest)
    terminal = {
        **{key: value for key, value in current.items() if key != "state_sha256"},
        "status": status,
        "error": error,
        "artifact_manifest_sha256": manifest["manifest_sha256"],
    }
    terminal["state_sha256"] = sha256_payload(terminal)
    atomic_write_json(state_path, terminal)
    return terminal
