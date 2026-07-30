#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2gR2_common import build_candidate, sha256_file, sha256_payload, verify_environment
from stage5c2gR2_state import atomic_write_json


def main() -> None:
    raise SystemExit("REJECTED: Stage 5C.2G-R2 cannot be finalized; use Stage 5C.2G-R3.1")
    parser = argparse.ArgumentParser()
    parser.add_argument("--custody-root")
    parser.add_argument("--external-receipt")
    parser.add_argument("--finalize", action="store_true")
    args = parser.parse_args()
    observed = verify_environment(); payload = build_candidate(ROOT, args.custody_root); candidate_sha = sha256_payload(payload)
    output = ROOT / "results/stage5c2gR2/protocol"; output.mkdir(parents=True, exist_ok=True)
    candidate_path = output / "CANDIDATE.json"; atomic_write_json(candidate_path, {**payload, "candidate_sha256": candidate_sha})
    if not args.finalize:
        print(json.dumps({"status": "AWAITING_EXTERNAL_TIMESTAMP", "candidate_sha256": candidate_sha, "runtime_files": len(payload["runtime_file_set"]), "config_hashes": payload["canonical_configs"], "plan_hashes": payload["expected_plans"], "environment": observed}, indent=2)); return
    if not args.external_receipt: raise SystemExit("--finalize requires --external-receipt")
    receipt_source = Path(args.external_receipt).resolve()
    if not receipt_source.is_file() or candidate_sha not in receipt_source.read_text(encoding="utf-8", errors="replace"): raise SystemExit("external receipt does not contain the reconstructed R2 candidate")
    receipt_target = output / "EXTERNAL_TIMESTAMP_RECEIPT.txt"; shutil.copy2(receipt_source, receipt_target)
    lock = {"stage": "stage5c2gR2_protocol_lock", "status": "LOCKED", "candidate_sha256": candidate_sha, "candidate_file": str(candidate_path.relative_to(ROOT)), "candidate_payload": payload, "receipt_path": str(receipt_target.relative_to(ROOT)), "receipt_sha256": sha256_file(receipt_target)}
    atomic_write_json(output / "LOCKED.json", lock)
    print(json.dumps({"status": "LOCKED", "candidate_sha256": candidate_sha, "runtime_files": len(payload["runtime_file_set"])}, indent=2))


if __name__ == "__main__": main()
