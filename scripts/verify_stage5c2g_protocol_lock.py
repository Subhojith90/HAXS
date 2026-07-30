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
from stage5c2g_common import load_yaml, sha256_file, sha256_payload


def covered_paths(protocol_path: Path, protocol: dict) -> list[Path]:
    stage = protocol["stage5c2g_protocol"]
    paths = [
        protocol_path, ROOT / "pyproject.toml", ROOT / "requirements.txt",
        ROOT / "STAGE5C2G_COMMANDS.sh", ROOT / "docs/stage5c2g/STAGE5C2G_RUNBOOK.md",
        ROOT / "docs/stage5c2g/CODE_DIFF_SUMMARY.md",
        ROOT / "scripts/run_stage5c2f_fresh_unzip_gate.py",
        ROOT / "src/haxs/methods/dtwa.py", ROOT / "src/haxs/methods/constrained_spin_hole.py",
        ROOT / "src/haxs/validation/topology.py",
    ]
    paths.extend(ROOT / value for value in stage["configs"].values())
    paths.extend(sorted((ROOT / "scripts").glob("*stage5c2g*.py")))
    paths.extend(sorted((ROOT / "tests/stage5c2g").glob("**/*")))
    return sorted({
        path.resolve()
        for path in paths
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix not in {".pyc", ".pyo"}
        and path.name != ".DS_Store"
    })


def verify_custody(protocol: dict) -> list[dict]:
    custody_path = ROOT / protocol["stage5c2g_protocol"]["configs"]["custody"]
    custody = load_yaml(custody_path)["stage5c2g_custody"]
    rows = []
    frozen_root = ROOT / custody["frozen_confirmation"]["root"]
    for relative, expected in custody["frozen_confirmation"]["files"].items():
        path = frozen_root / relative
        actual = sha256_file(path) if path.is_file() else "MISSING"
        rows.append({"path": str(path.relative_to(ROOT)), "expected": expected, "actual": actual, "passed": actual == expected})
    for relative, expected in custody["predecessor_stage5c2f_archives"].items():
        path = ROOT / relative
        actual = sha256_file(path) if path.is_file() else "MISSING"
        rows.append({"path": relative, "expected": expected, "actual": actual, "passed": actual == expected})
    return rows


def main() -> None:
    raise SystemExit("REJECTED LEGACY ROUTE: Stage 5C.2G is disabled; use Stage 5C.2G-R2")
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/stage5c2g/protocol.yaml")
    parser.add_argument("--out", default="results/stage5c2g/protocol_lock")
    parser.add_argument("--external-receipt", help="Externally timestamped file containing the published candidate SHA-256")
    parser.add_argument("--finalize", action="store_true")
    args = parser.parse_args()
    protocol_path = (ROOT / args.config).resolve()
    protocol = load_yaml(protocol_path)
    custody_rows = verify_custody(protocol)
    if not all(row["passed"] for row in custody_rows):
        raise SystemExit("custody verification failed; frozen predecessor material changed or is missing")
    covered = {str(path.relative_to(ROOT)): sha256_file(path) for path in covered_paths(protocol_path, protocol)}
    candidate = {
        "stage": "stage5c2g_protocol_lock_candidate",
        "protocol_version": protocol["stage5c2g_protocol"]["protocol_version"],
        "fixed_time": protocol["stage5c2g_protocol"]["fixed_time"],
        "primary_uncertainty_estimator": protocol["stage5c2g_protocol"]["primary_uncertainty_estimator"],
        "validity_gates": protocol["stage5c2g_protocol"]["validity_gates"],
        "covered_files": covered,
        "custody": custody_rows,
    }
    candidate_sha = sha256_payload(candidate)
    candidate["candidate_sha256"] = candidate_sha
    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    candidate_path = out / "CANDIDATE.json"
    candidate_path.write_text(json.dumps(candidate, indent=2) + "\n", encoding="utf-8")
    if not args.finalize:
        print(json.dumps({"status": "AWAITING_EXTERNAL_TIMESTAMP", "candidate_sha256": candidate_sha, "candidate_file": str(candidate_path.relative_to(ROOT)), "next": "Publish this SHA-256 externally, save the receipt, then rerun with --external-receipt RECEIPT --finalize"}, indent=2))
        return
    if not args.external_receipt:
        raise SystemExit("--finalize requires --external-receipt")
    receipt_source = Path(args.external_receipt).resolve()
    if not receipt_source.is_file():
        raise SystemExit("external timestamp receipt does not exist")
    receipt_target = out / "EXTERNAL_TIMESTAMP_RECEIPT.txt"
    shutil.copy2(receipt_source, receipt_target)
    receipt_text = receipt_target.read_text(encoding="utf-8", errors="replace")
    if candidate_sha not in receipt_text:
        raise SystemExit("external receipt does not contain the current candidate SHA-256")
    locked = {
        **candidate,
        "stage": "stage5c2g_protocol_lock",
        "status": "LOCKED_WITH_EXTERNAL_TIMESTAMP_RECEIPT",
        "finalized_at_utc": datetime.now(timezone.utc).isoformat(),
        "external_timestamp_receipt": {"stored_path": str(receipt_target.relative_to(ROOT)), "sha256": sha256_file(receipt_target)},
    }
    (out / "LOCKED.json").write_text(json.dumps(locked, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": locked["status"], "candidate_sha256": candidate_sha, "lock_file": str((out / "LOCKED.json").relative_to(ROOT))}, indent=2))


if __name__ == "__main__":
    main()
