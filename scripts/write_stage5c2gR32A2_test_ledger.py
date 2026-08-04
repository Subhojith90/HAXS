#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2gR32A2_common import atomic_write_json, sha256_payload

SUITES = {
    "full": ["tests"],
    "targeted": ["tests/stage5c2gR32A2", "tests/stage5c2gR32A1", "tests/stage5c2gR32A", "tests/regression"],
}


def collect(arguments: list[str]) -> list[str]:
    clean = {key: value for key, value in os.environ.items() if not key.startswith("PYTHON")}
    clean["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider", *arguments],
        cwd=ROOT, env=clean, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    if completed.returncode:
        raise RuntimeError(f"pytest collection failed:\n{completed.stdout}")
    nodeids = sorted({line.strip() for line in completed.stdout.splitlines() if line.startswith("tests/") and "::" in line})
    if not nodeids:
        raise RuntimeError("named-test collection is empty")
    return nodeids


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "results/stage5c2gR32A2/protocol/NAMED_TEST_LEDGER.json")
    args = parser.parse_args()
    if args.out.exists() or args.out.is_symlink():
        raise RuntimeError("refusing to overwrite named-test ledger")
    suites = {name: {"arguments": arguments, "nodeids": collect(arguments)} for name, arguments in SUITES.items()}
    counts = {name: len(record["nodeids"]) for name, record in suites.items()}
    payload = {"schema_version": "haxs.stage5c2gR32A2.named-tests.v1", "suites": suites, "counts": counts, "status": "PASS"}
    payload["ledger_sha256"] = sha256_payload(payload)
    atomic_write_json(args.out, payload)
    print(json.dumps({"status": "PASS", "counts": counts, "ledger_sha256": payload["ledger_sha256"]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
