#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2gR_common import build_candidate, sha256_file, sha256_payload


def main() -> None:
    raise SystemExit("REJECTED LEGACY ROUTE: candidate e65745... is disabled; use Stage 5C.2G-R2")
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/stage5c2gR/protocol.yaml")
    parser.add_argument("--out", default="results/stage5c2gR/protocol_lock")
    parser.add_argument("--custody-root")
    parser.add_argument("--external-receipt")
    parser.add_argument("--finalize", action="store_true")
    args = parser.parse_args()
    payload = build_candidate(args.config, ROOT, args.custody_root)
    candidate_sha = sha256_payload(payload)
    candidate = {**payload, "candidate_sha256": candidate_sha}
    output = ROOT / args.out
    output.mkdir(parents=True, exist_ok=True)
    candidate_path = output / "CANDIDATE.json"
    candidate_path.write_text(json.dumps(candidate, indent=2) + "\n", encoding="utf-8")
    if not args.finalize:
        print(json.dumps({"status": "AWAITING_EXTERNAL_TIMESTAMP", "candidate_sha256": candidate_sha, "source_files": len(payload["covered_files"]), "candidate_file": str(candidate_path.relative_to(ROOT))}, indent=2))
        return
    if not args.external_receipt:
        raise SystemExit("--finalize requires --external-receipt")
    receipt_source = Path(args.external_receipt).resolve()
    if not receipt_source.is_file():
        raise SystemExit("external timestamp receipt does not exist")
    receipt_text = receipt_source.read_text(encoding="utf-8", errors="replace")
    if candidate_sha not in receipt_text:
        raise SystemExit("external receipt does not contain the reconstructed candidate SHA-256")
    receipt_target = output / "EXTERNAL_TIMESTAMP_RECEIPT.txt"
    shutil.copy2(receipt_source, receipt_target)
    locked = {
        "stage": "stage5c2gR_protocol_lock",
        "status": "LOCKED_WITH_EXTERNAL_TIMESTAMP_RECEIPT",
        "candidate_sha256": candidate_sha,
        "candidate_file": str(candidate_path.relative_to(ROOT)),
        "candidate_payload": payload,
        "finalized_at_utc": datetime.now(timezone.utc).isoformat(),
        "external_timestamp_receipt": {"stored_path": str(receipt_target.relative_to(ROOT)), "sha256": sha256_file(receipt_target)},
    }
    (output / "LOCKED.json").write_text(json.dumps(locked, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": locked["status"], "candidate_sha256": candidate_sha, "source_files": len(payload["covered_files"]), "lock_file": str((output / "LOCKED.json").relative_to(ROOT))}, indent=2))


if __name__ == "__main__":
    main()
