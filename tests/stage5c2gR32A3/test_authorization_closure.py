from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_acceptance_contract_contains_three_supervisory_golden_negatives() -> None:
    ledger = json.loads(
        (ROOT / "configs/stage5c2gR32A3/adversarial_fixture_ledger.json").read_text(encoding="utf-8")
    )
    required = {
        "equal_count_unrelated_passing_tests",
        "nonzero_structured_command_exit",
        "host_records_share_wrong_actual_protocol",
    }
    assert required.issubset(ledger["invalid_fixtures"])
    assert ledger["required_outcome"] == "FAIL_BEFORE_RECEIPT_LOCK_OR_SCIENTIFIC_STATE"


def test_current_candidate_is_explicitly_superseded_and_never_receipt_eligible() -> None:
    ledger = json.loads(
        (ROOT / "configs/stage5c2gR32A3/supersession.json").read_text(encoding="utf-8")
    )
    assert ledger["predecessor_candidate_sha256"] == "24d6d3eb09b41feef6ef8858a300fc0ecbc9c9cf562bdc363d370ff528f2c9a4"
    assert ledger["receipt_eligible"] is False
    assert ledger["G1_authorized"] is False
