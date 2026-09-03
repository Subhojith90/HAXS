from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_a4_acceptance_contract_contains_required_new_failures() -> None:
    ledger = json.loads(
        (ROOT / "configs/stage5c2gR32A4/adversarial_fixture_ledger.json").read_text()
    )
    required = {
        "missing_junit_option", "duplicate_junit_option", "malformed_junit_target",
        "outside_root_junit_target", "symlinked_junit_target",
        "symlinked_junit_ancestor", "wrong_evidence_root", "missing_junit_output",
        "noncanonical_junit_target", "stale_host_b_package", "complete_return_tampering",
    }
    assert required.issubset(set(ledger["invalid_fixtures"]))


def test_a3_is_permanently_rejected_for_production_g0() -> None:
    supersession = json.loads(
        (ROOT / "configs/stage5c2gR32A4/supersession.json").read_text()
    )
    assert supersession["predecessor_candidate_sha256"] == (
        "03e02b4bc98a5fd116442b8453d8cf2f533c5f66c36a5b7868045d91b320f528"
    )
    assert supersession["production_g0_eligible"] is False
    assert supersession["receipt_eligible"] is False
