#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2gR32A5_common import atomic_write_json, sha256_file, sha256_payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--junit", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=ROOT / "results/stage5c2gR32A5/adversarial/OUTCOMES.json")
    args = parser.parse_args()
    if args.out.exists() or args.out.is_symlink():
        raise RuntimeError("refusing to overwrite R3.2A.5 outcomes")
    definition_path = ROOT / "configs/stage5c2gR32A5/adversarial_fixture_ledger.json"
    definition = json.loads(definition_path.read_text(encoding="utf-8"))
    xml = ElementTree.parse(args.junit).getroot()
    cases = list(xml.iter("testcase"))
    names = {f"{case.attrib.get('classname', '')}.{case.attrib.get('name', '')}" for case in cases}
    required_tests = {
        "test_wrong_identity_order_or_multiplicity_fails_closed",
        "test_nonpassing_testcase_fails_closed",
        "test_altered_command_exit_or_count_fails_closed",
        "test_wrong_argv_and_wrong_junit_binding_fail_closed",
        "test_finalizer_rejects_return_claim_that_differs_from_actual_protocol",
        "test_equal_host_claims_cannot_replace_actual_protocol_equality",
        "test_production_writer_record_round_trips_under_safe_root",
        "test_production_record_remains_verifiable_after_evidence_is_moved",
        "test_junit_target_mutations_fail_closed",
        "test_symlinked_junit_target_and_ancestor_fail_closed",
        "test_compileall_wrong_pycache_prefix_fails_closed",
        "test_isolated_compileall_writes_only_to_external_pycache",
        "test_complete_return_packager_binds_raw_primary_evidence",
        "test_complete_return_tampering_fails_before_comparison",
        "test_stale_predecessor_host_package_is_rejected",
        "test_valid_production_lifecycle_reaches_runner_exactly_once",
        "test_setup_failure_does_not_reserve_attempt_or_run",
        "test_control_plane_mutations_fail_closed",
        "test_execution_contract_mismatch_fails_before_reservation",
        "test_control_root_ancestor_symlink_fails_closed",
        "test_invalid_terminal_artifact_manifest_fails_closed",
        "test_runner_failure_terminalizes_once_and_does_not_retry",
        "test_two_concurrent_launches_execute_runner_once",
    }
    missing = [name for name in required_tests if not any(name in observed for observed in names)]
    failures = sum(len(case.findall("failure")) + len(case.findall("error")) + len(case.findall("skipped")) for case in cases)
    if missing or failures:
        raise RuntimeError(f"adversarial semantic suite failed: missing={missing} nonpass={failures}")
    payload = {
        "schema_version": "haxs.stage5c2gR32A5.adversarial-outcomes.v1",
        "status": "PASS", "junit_sha256": sha256_file(args.junit),
        "fixture_definition_sha256": sha256_file(definition_path),
        "invalid_fixture_count": len(definition["invalid_fixtures"]),
        "invalid_fixture_outcomes": {
            name: "FAIL_CLOSED_BEFORE_UNAUTHORIZED_RESERVATION_OR_EXECUTION"
            for name in definition["invalid_fixtures"]
        },
        "golden_fixture_outcomes": {
            name: "VALIDATED_LOCAL_LIFECYCLE_WITH_RUNNER_STUB_ONLY"
            for name in definition["golden_fixtures"]
        },
        "official_receipt_present": False,
        "official_scientific_state_present": False,
        "official_scientific_execution_performed": False,
    }
    payload["outcomes_sha256"] = sha256_payload(payload)
    atomic_write_json(args.out, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
