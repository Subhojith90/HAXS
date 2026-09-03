from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from finalize_stage5c2gR32A3_authorization import verify_complete_g0_return
from stage5c2gR32A2_common import sha256_payload
from stage5c2gR32A3_g0 import IDENTITY_FIELDS, verify_host_record


def test_fresh_unzip_entrypoint_bootstraps_sibling_imports_under_isolation() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            str(ROOT / "scripts/verify_stage5c2gR32A3_fresh_unzip.py"),
            "--help",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    assert completed.returncode == 0, completed.stdout


def test_finalizer_rejects_return_claim_that_differs_from_actual_protocol(tmp_path: Path) -> None:
    candidate = {
        "candidate_sha256": "a" * 64,
        "protocol_content_sha256": "b" * 64,
    }
    root = tmp_path / "return"
    root.mkdir()
    record = {
        "schema_version": "haxs.stage5c2gR32A3.complete-g0-return.v1",
        "candidate_sha256": candidate["candidate_sha256"],
        "protocol_archive_sha256": "d" * 64,
        "protocol_content_sha256": candidate["protocol_content_sha256"],
        "transport_container_sha256": "e" * 64,
        "host_a_path": "HOST_A.json", "host_b_path": "HOST_B.json",
        "comparison_path": "TWO_HOST_G0.json", "files": {},
        "scientific_execution_performed": False, "G1_authorized": False,
        "return_sha256": "",
    }
    record["return_sha256"] = sha256_payload(
        {key: value for key, value in record.items() if key != "return_sha256"}
    )
    (root / "G0_RETURN.json").write_text(json.dumps(record) + "\n", encoding="utf-8")
    with pytest.raises(RuntimeError):
        verify_complete_g0_return(root, candidate, "c" * 64)


def test_equal_host_claims_cannot_replace_actual_protocol_equality(tmp_path: Path) -> None:
    actual = "a" * 64
    false_shared_claim = "b" * 64
    candidate = {
        "candidate_sha256": "c" * 64,
        "authorization_contract": {},
    }
    host = {
        "schema_version": "haxs.stage5c2gR32A3.physical-host-g0.v1",
        "status": "PASS", "host_label": "HOST_A",
        **{field: "c" * 64 for field in IDENTITY_FIELDS},
        "protocol_archive_sha256": false_shared_claim,
        "physical_host": {}, "primary_evidence": {}, "test_counts": {},
        "semantic_evidence": {}, "scientific_execution_performed": False,
        "G1_authorized": False, "prior_authorization_present": False,
    }
    host["candidate_sha256"] = candidate["candidate_sha256"]
    path = tmp_path / "HOST_A.json"
    path.write_text(json.dumps(host) + "\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="actual-protocol binding failed"):
        verify_host_record(path, tmp_path, candidate, "HOST_A", actual)
