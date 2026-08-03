from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_PATH = ROOT / "results/stage5c2gR32A1/protocol/CANDIDATE.json"
LOCK_PATH = ROOT / "results/stage5c2gR32A1/protocol/LOCKED.json"
RECEIPT_PATH = (
    ROOT
    / "results/stage5c2gR32A1/protocol/SUPERVISOR_AUTHORIZATION_G1_ONLY.json"
)
STATE_PATH = ROOT / "results/stage5c2gR32A1/state/G1.json"

SCHEMA = "haxs.stage5c2gR32A1.authorization.v1"
DECISION = "ACCEPT_AND_AUTHORIZE_G1_ONLY"
BLOCKED_SCOPES = [
    "G2",
    "G3",
    "G4",
    "STAGE5C3",
    "STAGE5D",
    "MANUSCRIPT_RESULT_CLAIMS",
    "EXACT_MOBILE_HOLE_CLAIMS",
    "PUBLIC_RELEASE",
]
RECEIPT_KEYS = {
    "schema_version",
    "receipt_id",
    "decision",
    "candidate_sha256",
    "protocol_archive_sha256",
    "runtime_tree_sha256",
    "wheel_sha256",
    "environment_sha256",
    "g1_config_sha256",
    "g1_plan_sha256",
    "unit_registry_sha256",
    "runner_sha256",
    "test_ledger_sha256",
    "two_host_g0_sha256",
    "authorized_scope",
    "blocked_scopes",
    "issued_at_utc",
    "issuer",
}
MUTABLE_CURRENT_STAGE_PATHS = {
    "results/stage5c2gR32A1/protocol/LOCKED.json",
    "results/stage5c2gR32A1/protocol/SUPERVISOR_AUTHORIZATION_G1_ONLY.json",
    "results/stage5c2gR32A1/state/G1.json",
}
EXECUTABLE_SUFFIXES = {".py", ".sh", ".so", ".dylib", ".pyd"}


def sha256_file(path: str | Path) -> str:
    target = Path(path)
    digest = hashlib.sha256()
    with target.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_payload(payload: object) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    os.replace(temporary, path)


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
        raise RuntimeError(f"refusing to overwrite exclusive state: {path}") from error
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def load_candidate(root: Path = ROOT) -> dict:
    path = root / CANDIDATE_PATH.relative_to(ROOT)
    if not path.is_file() or path.is_symlink():
        raise RuntimeError("expected exactly one safe R3.2A.1 candidate record")
    candidate = json.loads(path.read_text(encoding="utf-8"))
    canonical = {key: value for key, value in candidate.items() if key != "candidate_sha256"}
    if candidate.get("candidate_sha256") != sha256_payload(canonical):
        raise RuntimeError("R3.2A.1 candidate self-identity failed")
    if candidate.get("schema_version") != "haxs.stage5c2gR32A1.candidate.v1":
        raise RuntimeError("predecessor or unknown candidate schema rejected")
    return candidate


def assert_runtime_files(candidate: dict, root: Path = ROOT) -> None:
    mismatches: list[str] = []
    for relative, expected in candidate["runtime_files"].items():
        path = root / relative
        if (
            not path.is_file()
            or path.is_symlink()
            or sha256_file(path) != expected
        ):
            mismatches.append(relative)
    if mismatches:
        raise RuntimeError(f"candidate runtime identity failed: {mismatches[:5]}")


def assert_root_closure(candidate: dict, root: Path = ROOT) -> None:
    mismatches: list[str] = []
    for relative, expected in candidate["root_closure_files"].items():
        path = root / relative
        if (
            not path.is_file()
            or path.is_symlink()
            or sha256_file(path) != expected
        ):
            mismatches.append(relative)
    if mismatches:
        raise RuntimeError(f"candidate root closure identity failed: {mismatches[:5]}")


def assert_no_unlisted_runtime(candidate: dict, root: Path = ROOT) -> None:
    symlinks = [
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_symlink()
    ]
    if symlinks:
        raise RuntimeError(f"symlink in execution root rejected: {symlinks[:5]}")
    observed = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in EXECUTABLE_SUFFIXES
    }
    expected = {
        relative
        for relative in candidate["runtime_files"]
        if Path(relative).suffix.lower() in EXECUTABLE_SUFFIXES
    }
    if observed != expected:
        raise RuntimeError(
            "execution-root executable set failed: "
            f"extra={sorted(observed-expected)[:5]} "
            f"missing={sorted(expected-observed)[:5]}"
        )


def _require_sha(value: object, field: str) -> str:
    text = str(value)
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        raise RuntimeError(f"receipt field is not a lowercase SHA-256: {field}")
    return text


def validate_receipt_payload(
    receipt: dict,
    candidate: dict,
    protocol_archive_sha256: str,
    two_host_g0_sha256: str,
) -> dict:
    if set(receipt) != RECEIPT_KEYS:
        raise RuntimeError("structured receipt has missing or additional keys")
    if receipt["schema_version"] != SCHEMA:
        raise RuntimeError("predecessor or unknown receipt schema rejected")
    if (
        receipt["decision"] != DECISION
        or receipt["authorized_scope"] != "G1_ONLY"
        or receipt["blocked_scopes"] != BLOCKED_SCOPES
    ):
        raise RuntimeError("receipt decision, scope, or ordered downstream blocks failed")
    try:
        uuid.UUID(str(receipt["receipt_id"]))
    except ValueError as error:
        raise RuntimeError("receipt ID must be a UUID") from error
    if set(receipt["issuer"]) != {"name", "role"}:
        raise RuntimeError("receipt issuer must use the exact schema")
    if (
        receipt["issuer"]["role"] != "SUPERVISOR"
        or not str(receipt["issuer"]["name"]).strip()
    ):
        raise RuntimeError("receipt issuer identity failed")
    try:
        issued = datetime.fromisoformat(
            str(receipt["issued_at_utc"]).replace("Z", "+00:00")
        )
    except ValueError as error:
        raise RuntimeError("receipt timestamp is not ISO-8601") from error
    if issued.tzinfo is None or issued.utcoffset() != timezone.utc.utcoffset(issued):
        raise RuntimeError("receipt timestamp must be explicitly UTC")

    contracts = candidate["authorization_contract"]
    expected = {
        "candidate_sha256": candidate["candidate_sha256"],
        "protocol_archive_sha256": protocol_archive_sha256,
        "runtime_tree_sha256": candidate["runtime_tree_sha256"],
        "wheel_sha256": candidate["wheel"]["sha256"],
        "environment_sha256": candidate["environment"]["sha256"],
        "g1_config_sha256": contracts["g1_config"]["sha256"],
        "g1_plan_sha256": contracts["g1_plan"]["sha256"],
        "unit_registry_sha256": contracts["unit_registry"]["sha256"],
        "runner_sha256": contracts["runner"]["sha256"],
        "test_ledger_sha256": contracts["test_ledger"]["sha256"],
        "two_host_g0_sha256": two_host_g0_sha256,
    }
    mismatches = [
        field
        for field, expected_value in expected.items()
        if _require_sha(receipt[field], field) != expected_value
    ]
    if mismatches:
        raise RuntimeError(f"receipt identity mismatch: {mismatches}")
    return receipt


def load_and_validate_receipt(
    path: Path,
    candidate: dict,
    protocol_archive_sha256: str,
    two_host_g0_sha256: str,
) -> dict:
    if not path.is_file() or path.is_symlink():
        raise RuntimeError("structured receipt is missing or unsafe")
    def exact_object(pairs: list[tuple[str, object]]) -> dict:
        payload: dict = {}
        for key, value in pairs:
            if key in payload:
                raise RuntimeError(f"duplicate structured-receipt key: {key}")
            payload[key] = value
        return payload

    try:
        receipt = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=exact_object
        )
    except json.JSONDecodeError as error:
        raise RuntimeError("supervisor receipt must be strict JSON") from error
    if not isinstance(receipt, dict):
        raise RuntimeError("supervisor receipt must be a JSON object")
    return validate_receipt_payload(
        receipt, candidate, protocol_archive_sha256, two_host_g0_sha256
    )


def load_lock(candidate: dict, root: Path = ROOT) -> dict:
    path = root / LOCK_PATH.relative_to(ROOT)
    if not path.is_file() or path.is_symlink():
        raise RuntimeError("official R3.2A.1 G1 is blocked pending a valid lock")
    lock = json.loads(path.read_text(encoding="utf-8"))
    canonical = {key: value for key, value in lock.items() if key != "lock_sha256"}
    contracts = candidate["authorization_contract"]
    bound_fields = {
        "runtime_tree_sha256": candidate["runtime_tree_sha256"],
        "wheel_sha256": candidate["wheel"]["sha256"],
        "environment_sha256": candidate["environment"]["sha256"],
        "g1_config_sha256": contracts["g1_config"]["sha256"],
        "g1_plan_sha256": contracts["g1_plan"]["sha256"],
        "unit_registry_sha256": contracts["unit_registry"]["sha256"],
        "runner_sha256": contracts["runner"]["sha256"],
        "test_ledger_sha256": contracts["test_ledger"]["sha256"],
        "root_manifest_sha256": contracts["root_manifest"]["sha256"],
    }
    if (
        lock.get("lock_sha256") != sha256_payload(canonical)
        or lock.get("schema_version") != "haxs.stage5c2gR32A1.lock.v1"
        or lock.get("status") != "LOCKED_G1_ONLY"
        or lock.get("authorized_scope") != "G1_ONLY"
        or lock.get("candidate_sha256") != candidate["candidate_sha256"]
        or lock.get("official_attempt_limit") != 1
        or lock.get("same_candidate_retry_forbidden") is not True
        or lock.get("blocked_scopes") != BLOCKED_SCOPES
        or any(lock.get(field) != value for field, value in bound_fields.items())
    ):
        raise RuntimeError("R3.2A.1 lock identity, scope, or attempt policy failed")
    receipt = root / lock["receipt_path"]
    if (
        not receipt.is_file()
        or receipt.is_symlink()
        or sha256_file(receipt) != lock["receipt_sha256"]
    ):
        raise RuntimeError("locked structured receipt changed or is missing")
    structured = load_and_validate_receipt(
        receipt,
        candidate,
        lock["protocol_archive_sha256"],
        lock["two_host_g0_sha256"],
    )
    if structured["receipt_id"] != lock.get("receipt_id"):
        raise RuntimeError("locked receipt UUID differs from the structured receipt")
    return lock


def reserve_attempt(candidate: dict, lock: dict, root: Path = ROOT) -> dict:
    state_path = root / STATE_PATH.relative_to(ROOT)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    attempt_id = uuid.uuid4().hex
    artifact = (
        root
        / "results/stage5c2gR32A1/artifacts"
        / candidate["candidate_sha256"]
        / "G1"
        / attempt_id
    )
    running = {
        "schema_version": "haxs.stage5c2gR32A1.single-attempt-state.v1",
        "gate": "G1",
        "status": "RUNNING",
        "sequence": 1,
        "attempt_id": attempt_id,
        "candidate_sha256": candidate["candidate_sha256"],
        "receipt_id": lock["receipt_id"],
        "artifact_path": artifact.relative_to(root).as_posix(),
        "error": "",
    }
    running["state_sha256"] = sha256_payload(running)
    data = (json.dumps(running, indent=2, sort_keys=True) + "\n").encode("utf-8")
    try:
        descriptor = os.open(
            state_path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH,
        )
    except FileExistsError as error:
        raise RuntimeError(
            "official R3.2A.1 G1 has already been attempted; retry forbidden"
        ) from error
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    return running


def terminalize_attempt(
    running: dict,
    status: str,
    details: dict,
    root: Path = ROOT,
) -> dict:
    if status not in {"PASSED", "FAILED"}:
        raise ValueError("terminal state must be PASSED or FAILED")
    state_path = root / STATE_PATH.relative_to(ROOT)
    current = json.loads(state_path.read_text(encoding="utf-8"))
    if (
        current.get("status") != "RUNNING"
        or current.get("attempt_id") != running["attempt_id"]
        or current.get("state_sha256")
        != sha256_payload({key: value for key, value in current.items() if key != "state_sha256"})
    ):
        raise RuntimeError("atomic G1 running state changed before terminalization")
    terminal = {
        **{key: value for key, value in running.items() if key != "state_sha256"},
        "status": status,
        **details,
    }
    terminal["state_sha256"] = sha256_payload(terminal)
    atomic_write_json(state_path, terminal)
    return terminal
