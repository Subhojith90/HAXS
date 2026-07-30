#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2gR3_common import build_candidate, require_isolated_interpreter, sha256_file, sha256_payload
from stage5c2gR3_receipt import load_and_validate_receipt
from stage5c2gR3_state import atomic_write_json


def main() -> None:
    require_isolated_interpreter(ROOT)
    parser = argparse.ArgumentParser(); parser.add_argument("--external-receipt", required=True); parser.add_argument("--protocol-archive", required=True); parser.add_argument("--custody-root", required=True); args = parser.parse_args()
    payload = build_candidate(ROOT, args.custody_root); candidate_sha = sha256_payload(payload)
    candidate = {**payload, "candidate_sha256": candidate_sha}
    receipt_source = Path(args.external_receipt).resolve()
    archive_source = Path(args.protocol_archive).resolve()
    structured_receipt = load_and_validate_receipt(receipt_source, candidate, archive_source)
    output = ROOT / "results/stage5c2gR3/protocol"; output.mkdir(parents=True, exist_ok=True)
    candidate_path = output / "CANDIDATE.json"; atomic_write_json(candidate_path, candidate)
    receipt_target = output / "SUPERVISOR_AUTHORIZATION_G1_ONLY.json"; shutil.copy2(receipt_source, receipt_target)
    lock = {"stage": "stage5c2gR3_1_protocol_lock", "status": "LOCKED_G1_ONLY", "candidate_sha256": candidate_sha, "candidate_file": str(candidate_path.relative_to(ROOT)), "candidate_payload": payload, "receipt_path": str(receipt_target.relative_to(ROOT)), "receipt_sha256": sha256_file(receipt_target), "receipt_id": structured_receipt["receipt_id"], "authorized_scope": structured_receipt["authorized_scope"], "protocol_archive_path": str(archive_source), "protocol_archive_sha256": sha256_file(archive_source)}
    atomic_write_json(output / "LOCKED.json", lock)
    print(json.dumps({"status": "LOCKED_AFTER_STRUCTURED_SUPERVISORY_AUTHORIZATION", "authorized_scope": "G1_ONLY", "candidate_sha256": candidate_sha, "receipt_id": structured_receipt["receipt_id"]}, indent=2))


if __name__ == "__main__": main()
