from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pandas as pd

from stage5c2gR2_common import PLAN_BUILDERS, ROOT, canonical_config, sha256_file, sha256_payload

REQUIRED_ROLES = {"G1": {"curves", "comparisons", "registry", "attempts"}}


def atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name); handle.write(json.dumps(payload, indent=2) + "\n"); handle.flush(); os.fsync(handle.fileno())
    os.replace(temporary, path)


def write_gate_state(gate: str, status: str, lock: dict, config_sha: str, plan_sha: str, attempt_id: str, manifest_path: str | None = None, manifest_sha: str | None = None, error: str = "", root: Path = ROOT) -> dict:
    path = root / f"results/stage5c2gR2/state/{gate}.json"
    previous_sequence = 0
    if path.is_file(): previous_sequence = int(json.loads(path.read_text(encoding="utf-8")).get("sequence", 0))
    payload = {"stage": "stage5c2gR2_atomic_gate_state", "gate": gate, "status": status, "sequence": previous_sequence + 1, "candidate_sha256": lock["candidate_sha256"], "canonical_config_sha256": config_sha, "expected_plan_sha256": plan_sha, "attempt_id": attempt_id, "manifest_path": manifest_path, "manifest_sha256": manifest_sha, "error": error}
    payload["state_sha256"] = sha256_payload(payload); atomic_write_json(path, payload); return payload


def build_raw_manifest(gate: str, attempt_root: Path, files: dict[str, Path], expected_ids: list[str], observed_ids: list[str], lock: dict, config_sha: str, plan_sha: str, attempt_id: str) -> dict:
    if sorted(observed_ids) != sorted(expected_ids) or len(observed_ids) != len(set(observed_ids)): raise RuntimeError("observed IDs do not equal the unique expected plan")
    if gate in REQUIRED_ROLES and set(files) != REQUIRED_ROLES[gate]: raise RuntimeError(f"raw manifest roles differ from canonical {gate} roles")
    records = {}
    for role, path in sorted(files.items()):
        frame = pd.read_csv(path)
        identifier = "comparison_id" if gate == "G1" else "run_id"
        if identifier in frame.columns:
            file_ids = frame[identifier].astype(str).tolist()
            if sorted(file_ids) != sorted(expected_ids) or len(file_ids) != len(set(file_ids)): raise RuntimeError(f"{role} IDs differ from canonical expected IDs")
        records[role] = {"path": path.name, "sha256": sha256_file(path), "rows": len(frame)}
    payload = {"stage": "stage5c2gR2_raw_output_manifest", "gate": gate, "attempt_id": attempt_id, "candidate_sha256": lock["candidate_sha256"], "canonical_config_sha256": config_sha, "expected_plan_sha256": plan_sha, "expected_ids": sorted(expected_ids), "observed_ids": sorted(observed_ids), "files": records}
    payload["manifest_sha256"] = sha256_payload(payload); return payload


def verify_raw_manifest(path: str | Path, lock: dict, gate: str, root: Path = ROOT) -> dict:
    manifest_path = Path(path)
    if not manifest_path.is_absolute(): manifest_path = root / manifest_path
    payload = json.loads(manifest_path.read_text(encoding="utf-8")); canonical = {k: v for k, v in payload.items() if k != "manifest_sha256"}
    if payload.get("manifest_sha256") != sha256_payload(canonical): raise RuntimeError("raw manifest digest failed")
    config, config_sha, plan_sha = canonical_config(gate, lock, root)
    if payload.get("candidate_sha256") != lock["candidate_sha256"] or payload.get("canonical_config_sha256") != config_sha or payload.get("expected_plan_sha256") != plan_sha: raise RuntimeError("raw manifest identity failed")
    identifier = "comparison_id" if gate == "G1" else "run_id"
    canonical_ids = sorted(str(row[identifier]) for row in PLAN_BUILDERS[gate](config))
    if payload.get("expected_ids") != canonical_ids: raise RuntimeError("raw manifest expected IDs differ from reconstructed canonical plan")
    if gate in REQUIRED_ROLES and set(payload.get("files", {})) != REQUIRED_ROLES[gate]: raise RuntimeError("raw manifest required roles failed")
    if payload.get("expected_ids") != payload.get("observed_ids") or len(payload["observed_ids"]) != len(set(payload["observed_ids"])): raise RuntimeError("raw manifest run IDs failed")
    expected_files = {record["path"] for record in payload["files"].values()} | {manifest_path.name}
    actual_files = {item.name for item in manifest_path.parent.iterdir() if item.is_file()}
    if actual_files != expected_files: raise RuntimeError(f"unexpected or missing raw artifact files: {sorted(actual_files ^ expected_files)}")
    for record in payload["files"].values():
        file_path = manifest_path.parent / record["path"]
        if sha256_file(file_path) != record["sha256"] or len(pd.read_csv(file_path)) != int(record["rows"]): raise RuntimeError(f"raw artifact changed: {file_path}")
    return payload


def verify_gate_state(gate: str, lock: dict, root: Path = ROOT) -> dict:
    path = root / f"results/stage5c2gR2/state/{gate}.json"; state = json.loads(path.read_text(encoding="utf-8")); canonical = {k: v for k, v in state.items() if k != "state_sha256"}
    if state.get("state_sha256") != sha256_payload(canonical): raise RuntimeError("gate state digest failed")
    if state.get("gate") != gate or state.get("status") != "PASSED" or state.get("candidate_sha256") != lock["candidate_sha256"]: raise RuntimeError("latest atomic gate state is not a current PASS")
    _, config_sha, plan_sha = canonical_config(gate, lock, root)
    if state.get("canonical_config_sha256") != config_sha or state.get("expected_plan_sha256") != plan_sha: raise RuntimeError("gate state config/plan identity failed")
    manifest = verify_raw_manifest(state["manifest_path"], lock, gate, root)
    if state.get("manifest_sha256") != manifest["manifest_sha256"] or state.get("attempt_id") != manifest["attempt_id"]: raise RuntimeError("gate state does not bind verified raw evidence")
    return state


def verify_supervisor_authorization(receipt_path: str | Path, gate: str, lock: dict, root: Path = ROOT) -> dict:
    """Recompute the gate and evidence first; never trust a supplied digest."""
    state = verify_gate_state(gate, lock, root)
    receipt = Path(receipt_path)
    if not receipt.is_absolute(): receipt = root / receipt
    if not receipt.is_file(): raise RuntimeError("supervisor authorization receipt is missing")
    text = receipt.read_text(encoding="utf-8", errors="replace")
    required = [lock["candidate_sha256"], state["state_sha256"], state["manifest_sha256"], state["attempt_id"]]
    if not all(value in text for value in required): raise RuntimeError("supervisor receipt does not bind recomputed candidate/gate/manifest/attempt identity")
    return state
