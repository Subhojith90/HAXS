from __future__ import annotations

import uuid
from pathlib import Path

from stage5c2gR32A2_common import (
    assert_exact_membership, assert_no_forbidden_import_artifacts, atomic_write_json,
    exclusive_write_json, safe_relative, sha256_file, sha256_payload, strict_json,
    tree_snapshot, verify_record,
)

ROOT = Path(__file__).resolve().parents[1]
STAGE = "stage5c2gR32A3"
CANDIDATE_PATH = ROOT / "results/stage5c2gR32A3/protocol/CANDIDATE.json"
ROOT_MANIFEST_PATH = ROOT / "results/stage5c2gR32A3/protocol/ROOT_MANIFEST.json"
LOCK_PATH = ROOT / "results/stage5c2gR32A3/protocol/LOCKED.json"
RECEIPT_PATH = ROOT / "results/stage5c2gR32A3/protocol/SUPERVISOR_AUTHORIZATION_G1_ONLY.json"
AUTHORIZATION_PATH = ROOT / "results/stage5c2gR32A3/protocol/AUTHORIZATION.json"
STATE_PATH = ROOT / "results/stage5c2gR32A3/state/G1.json"
SETUP_STATE_PATH = ROOT / "results/stage5c2gR32A3/preflight/SETUP.json"


def load_candidate(root: Path = ROOT) -> dict:
    candidate = strict_json(root / CANDIDATE_PATH.relative_to(ROOT))
    canonical = {key: value for key, value in candidate.items() if key != "candidate_sha256"}
    if candidate.get("schema_version") != "haxs.stage5c2gR32A3.candidate.v1":
        raise RuntimeError("predecessor or unknown candidate schema rejected")
    if candidate.get("candidate_sha256") != sha256_payload(canonical):
        raise RuntimeError("R3.2A.3 candidate self-identity failed")
    return candidate


def reserve_attempt(candidate: dict, authorization: dict, root: Path = ROOT) -> dict:
    state_path = root / STATE_PATH.relative_to(ROOT)
    attempt_id = uuid.uuid4().hex
    artifact = root / "results/stage5c2gR32A3/artifacts" / candidate["candidate_sha256"] / "G1" / attempt_id
    running = {
        "schema_version": "haxs.stage5c2gR32A3.single-attempt-state.v1",
        "gate": "G1", "status": "RUNNING", "sequence": 1,
        "attempt_id": attempt_id, "candidate_sha256": candidate["candidate_sha256"],
        "receipt_id": authorization["receipt"]["receipt_id"],
        "artifact_path": artifact.relative_to(root).as_posix(), "error": "",
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
