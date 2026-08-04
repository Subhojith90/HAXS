#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2gR32A2_common import (
    AUTHORIZATION_PATH, LOCK_PATH, RECEIPT_PATH, STATE_PATH,
    atomic_write_json, sha256_file, sha256_payload,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--junit", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=ROOT / "results/stage5c2gR32A2/adversarial/OUTCOMES.json")
    args = parser.parse_args()
    if args.out.exists() or args.out.is_symlink():
        raise RuntimeError("refusing to overwrite adversarial outcome ledger")
    expected_path = ROOT / "configs/stage5c2gR32A2/adversarial_fixture_ledger.json"
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    xml = ElementTree.parse(args.junit).getroot()
    suites = [xml] if xml.tag == "testsuite" else list(xml.findall("testsuite"))
    tests = sum(int(suite.attrib.get("tests", "0")) for suite in suites)
    failures = sum(int(suite.attrib.get("failures", "0")) + int(suite.attrib.get("errors", "0")) for suite in suites)
    if tests < len(expected["invalid_fixtures"]) or failures:
        raise RuntimeError(f"adversarial JUnit failed: tests={tests} failures={failures}")
    forbidden = [ROOT / path.relative_to(ROOT) for path in [AUTHORIZATION_PATH, LOCK_PATH, RECEIPT_PATH, STATE_PATH]]
    present = [path.relative_to(ROOT).as_posix() for path in forbidden if path.exists() or path.is_symlink()]
    if present:
        raise RuntimeError(f"adversarial suite left forbidden authorization/state: {present}")
    payload = {
        "schema_version": "haxs.stage5c2gR32A2.adversarial-outcomes.v1",
        "status": "PASS", "junit_sha256": sha256_file(args.junit),
        "fixture_definition_sha256": sha256_file(expected_path),
        "invalid_fixture_count": len(expected["invalid_fixtures"]),
        "invalid_fixture_outcomes": {name: "FAIL_CLOSED_BEFORE_AUTHORIZATION_OR_STATE" for name in expected["invalid_fixtures"]},
        "golden_fixture_outcomes": {name: "VALIDATED_DRY_RUN_WITHOUT_AUTHORIZATION_OR_STATE" for name in expected["golden_fixtures"]},
        "receipt_present": False, "lock_present": False, "scientific_state_present": False,
    }
    payload["outcomes_sha256"] = sha256_payload(payload)
    atomic_write_json(args.out, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
