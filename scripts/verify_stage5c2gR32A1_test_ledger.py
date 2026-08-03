#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))
from stage5c2gR32A1_authorization import ROOT, load_candidate, sha256_file
from write_stage5c2gR32A1_test_ledger import collect


def verify_ledger(path: Path) -> dict:
    if not path.is_file() or path.is_symlink():
        raise RuntimeError("named-test ledger is missing or unsafe")
    candidate = load_candidate()
    bound = candidate["authorization_contract"]["test_ledger"]
    if (
        path.resolve() != (ROOT / bound["path"]).resolve()
        or sha256_file(path) != bound["sha256"]
    ):
        raise RuntimeError("named-test ledger differs from candidate identity")
    ledger = json.loads(path.read_text(encoding="utf-8"))
    if (
        ledger.get("schema_version")
        != "haxs.stage5c2gR32A1.named-tests.v1"
        or set(ledger.get("suites", {})) != {"full", "targeted"}
    ):
        raise RuntimeError("named-test ledger schema or suites failed")
    counts = {}
    for name, record in ledger["suites"].items():
        observed = collect(list(record["arguments"]))
        if observed != record["nodeids"]:
            raise RuntimeError(f"named-test collection changed: {name}")
        counts[name] = len(observed)
    return {"status": "PASS", "counts": counts, "ledger_sha256": sha256_file(path)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ledger",
        type=Path,
        default=ROOT / "results/stage5c2gR32A1/protocol/NAMED_TEST_LEDGER.json",
    )
    args = parser.parse_args()
    print(json.dumps(verify_ledger(args.ledger), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
