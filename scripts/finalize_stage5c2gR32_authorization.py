#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2gR32_common import atomic_write_json, sha256_file, sha256_payload

BLOCKED = [
    "G2",
    "G3",
    "G4",
    "STAGE5C3",
    "STAGE5D",
    "MANUSCRIPT_RESULT_CLAIMS",
    "EXACT_MOBILE_HOLE_CLAIMS",
    "PUBLIC_RELEASE",
]


def _candidate() -> dict:
    choices = [
        ROOT / "CANDIDATE.stage5c2gR32.json",
        ROOT / "results/stage5c2gR32/protocol/CANDIDATE.json",
    ]
    records = [path for path in choices if path.is_file()]
    if len(records) != 1:
        raise RuntimeError("expected exactly one R3.2 candidate record")
    candidate = json.loads(records[0].read_text(encoding="utf-8"))
    canonical = {key: value for key, value in candidate.items() if key != "candidate_sha256"}
    if candidate.get("candidate_sha256") != sha256_payload(canonical):
        raise RuntimeError("candidate self-identity failed")
    return candidate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--protocol-archive", required=True, type=Path)
    parser.add_argument("--two-host-g0", required=True, type=Path)
    args = parser.parse_args()
    lock_path = ROOT / "results/stage5c2gR32/protocol/LOCKED.json"
    if lock_path.exists():
        raise RuntimeError("R3.2 authorization is already finalized")
    candidate = _candidate()
    two_host = json.loads(args.two_host_g0.read_text(encoding="utf-8"))
    if (
        two_host.get("status") != "PASS"
        or two_host["host_a"].get("candidate_sha256") != candidate["candidate_sha256"]
        or two_host["host_b"].get("candidate_sha256") != candidate["candidate_sha256"]
        or two_host["host_a"]["physical_host"]["physical_host_sha256"]
        == two_host["host_b"]["physical_host"]["physical_host_sha256"]
    ):
        raise RuntimeError("two physically distinct clean-host G0 evidence is not accepted")
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    required = {
        "schema_version",
        "receipt_id",
        "decision",
        "candidate_sha256",
        "protocol_archive_sha256",
        "runtime_tree_sha256",
        "authorized_scope",
        "blocked_scopes",
        "issued_at_utc",
        "issuer",
    }
    if set(receipt) != required:
        raise RuntimeError("structured R3.2 receipt has missing or extra keys")
    if (
        receipt["schema_version"] != "haxs.stage5c2gR32.authorization.v1"
        or receipt["decision"] != "ACCEPT_AND_AUTHORIZE_G1_ONLY"
        or receipt["candidate_sha256"] != candidate["candidate_sha256"]
        or receipt["protocol_archive_sha256"] != sha256_file(args.protocol_archive)
        or receipt["runtime_tree_sha256"] != candidate["runtime_tree_sha256"]
        or receipt["authorized_scope"] != "G1_ONLY"
        or receipt["blocked_scopes"] != BLOCKED
        or receipt.get("issuer", {}).get("role") != "SUPERVISOR"
        or not str(receipt.get("issuer", {}).get("name", "")).strip()
    ):
        raise RuntimeError("structured R3.2 receipt identity or scope failed")
    issued = datetime.fromisoformat(receipt["issued_at_utc"].replace("Z", "+00:00"))
    if issued.tzinfo is None:
        raise RuntimeError("structured receipt timestamp must include UTC offset")
    destination = (
        ROOT / "results/stage5c2gR32/protocol/SUPERVISOR_AUTHORIZATION_G1_ONLY.json"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(args.receipt, destination)
    lock = {
        "schema_version": "haxs.stage5c2gR32.lock.v1",
        "status": "LOCKED_G1_ONLY",
        "authorized_scope": "G1_ONLY",
        "candidate_sha256": candidate["candidate_sha256"],
        "runtime_tree_sha256": candidate["runtime_tree_sha256"],
        "wheel_sha256": candidate["wheel"]["sha256"],
        "protocol_archive_sha256": sha256_file(args.protocol_archive),
        "receipt_id": receipt["receipt_id"],
        "receipt_sha256": sha256_file(destination),
        "receipt_path": destination.relative_to(ROOT).as_posix(),
        "two_host_g0_sha256": sha256_file(args.two_host_g0),
        "blocked_scopes": BLOCKED,
        "official_attempt_limit": 1,
        "same_candidate_retry_forbidden": True,
    }
    lock["lock_sha256"] = sha256_payload(lock)
    atomic_write_json(lock_path, lock)
    print(
        json.dumps(
            {
                "status": "LOCKED_AFTER_NEW_STRUCTURED_SUPERVISORY_AUTHORIZATION",
                "candidate_sha256": candidate["candidate_sha256"],
                "receipt_id": receipt["receipt_id"],
                "authorized_scope": "G1_ONLY",
                "next": "ONE_OFFICIAL_G1_THEN_STOP",
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
