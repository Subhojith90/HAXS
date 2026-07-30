from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from stage5c2gR_common import sha256_file, sha256_payload


def create_chunk_manifest(
    chunk_id: str,
    files: dict[str, Path],
    expected_run_ids: list[str],
    protocol_candidate_sha256: str,
    config_sha256: str,
) -> dict:
    expected = sorted(expected_run_ids)
    attempts = pd.read_csv(files["attempts"])
    observed = sorted(attempts.run_id.astype(str).tolist())
    if observed != expected or attempts.run_id.duplicated().any() or not attempts.status.eq("completed").all():
        raise RuntimeError(f"chunk {chunk_id} does not contain exactly the expected completed run IDs")
    records = {}
    for role, path in sorted(files.items()):
        frame = pd.read_csv(path)
        records[role] = {"path": path.name, "sha256": sha256_file(path), "rows": int(len(frame))}
    payload = {"stage": "stage5c2gR_fixed_count_chunk", "chunk_id": chunk_id, "status": "COMPLETE", "protocol_candidate_sha256": protocol_candidate_sha256, "config_sha256": config_sha256, "expected_run_ids": expected, "files": records, "all_attempts_completed": True}
    payload["manifest_sha256"] = sha256_payload(payload)
    return payload


def validate_chunk_manifest(path: str | Path, expected_run_ids: list[str], protocol_candidate_sha256: str, config_sha256: str) -> dict:
    manifest_path = Path(path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    canonical = {key: value for key, value in payload.items() if key != "manifest_sha256"}
    if payload.get("manifest_sha256") != sha256_payload(canonical): raise RuntimeError(f"chunk manifest payload hash failed: {manifest_path}")
    if payload.get("status") != "COMPLETE" or not payload.get("all_attempts_completed"): raise RuntimeError(f"chunk is incomplete: {manifest_path}")
    if payload.get("protocol_candidate_sha256") != protocol_candidate_sha256 or payload.get("config_sha256") != config_sha256: raise RuntimeError(f"chunk identity mismatch: {manifest_path}")
    if payload.get("expected_run_ids") != sorted(expected_run_ids): raise RuntimeError(f"chunk expected-ID mismatch: {manifest_path}")
    for record in payload["files"].values():
        file_path = manifest_path.parent / record["path"]
        if not file_path.is_file() or sha256_file(file_path) != record["sha256"] or len(pd.read_csv(file_path)) != int(record["rows"]): raise RuntimeError(f"chunk file integrity failed: {file_path}")
    return payload

