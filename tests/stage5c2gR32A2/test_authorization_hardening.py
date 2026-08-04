from __future__ import annotations

import copy
import base64
import hashlib
import json
import sys
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import finalize_stage5c2gR32A2_authorization as finalizer
from finalize_stage5c2gR32A2_authorization import BLOCKED_SCOPES, RECEIPT_KEYS, validate_receipt
from launch_stage5c2gR32A2_G1_isolated import preflight_and_reserve
from stage5c2gR32A2_common import (
    AUTHORIZATION_PATH, LOCK_PATH, RECEIPT_PATH, SETUP_STATE_PATH, STATE_PATH,
    assert_exact_membership, assert_no_forbidden_import_artifacts, sha256_file, sha256_payload,
)
from stage5c2gR32A2_g0 import finalize_comparison, recompute_two_host_g0
from verify_stage5c2gR32A2_environment import installed_wheel_tree_identity
from build_stage5c2gR32A2_candidate import closure_paths

SHA = "a" * 64
OTHER = "b" * 64


def test_retained_full_suite_compatibility_artifacts_are_candidate_bound() -> None:
    relative_paths = {
        path.relative_to(ROOT).as_posix(): path for path in closure_paths()
    }
    required = {
        "output/stage5c2gR32/sanity_calibration/calibration_decision.json",
        "output/stage5c2gR32A1/haxs-0.8.4-py3-none-any.whl",
    }
    assert required.issubset(relative_paths)
    for relative in required:
        path = relative_paths[relative]
        assert path.is_file()
        assert not path.is_symlink()


def test_official_g0_enforces_read_only_root_and_nested_bytecode_is_disabled() -> None:
    wrapper = (ROOT / "run_stage5c2gR32A2_G0.sh").read_text(encoding="utf-8")
    predecessor_tests = (
        ROOT / "tests/stage5c2gR3/test_stage5c2gR3_adversarial.py"
    ).read_text(encoding="utf-8")
    assert 'chmod -R a-w "$ROOT"' in wrapper
    assert '[sys.executable, "-I", "-B", "scripts/check_stage5c2gR3_static_gate.py"]' in predecessor_tests
    assert '[sys.executable, "-I", "-B", "scripts/verify_stage5c2gR32A1_immutable_install.py"]' in predecessor_tests


def candidate() -> dict:
    contracts = {name: {"path": f"fixture/{name}", "sha256": SHA} for name in [
        "root_manifest", "g1_config", "g1_plan", "unit_registry", "runner",
        "test_ledger", "launcher", "adversarial_outcomes",
    ]}
    return {
        "candidate_sha256": SHA, "runtime_tree_sha256": SHA,
        "wheel": {"path": "fixture.whl", "sha256": SHA},
        "environment": {"path": "environment.json", "sha256": SHA},
        "dependency_lock": {"path": "requirements.lock", "sha256": SHA},
        "wheelhouse_manifest": {"path": "wheelhouse.txt", "sha256": SHA},
        "authorization_contract": contracts,
    }


def receipt() -> dict:
    return {
        "schema_version": "haxs.stage5c2gR32A2.authorization.v1",
        "receipt_id": str(uuid.uuid4()), "decision": "ACCEPT_AND_AUTHORIZE_G1_ONLY",
        "candidate_sha256": SHA, "protocol_archive_sha256": SHA,
        "runtime_tree_sha256": SHA, "wheel_sha256": SHA, "environment_sha256": SHA,
        "g1_config_sha256": SHA, "g1_plan_sha256": SHA, "unit_registry_sha256": SHA,
        "runner_sha256": SHA, "test_ledger_sha256": SHA, "g0_return_sha256": SHA,
        "two_host_g0_sha256": SHA, "authorized_scope": "G1_ONLY",
        "blocked_scopes": list(BLOCKED_SCOPES),
        "issued_at_utc": datetime.now(timezone.utc).isoformat(),
        "issuer": {"name": "Supervisor Fixture", "role": "SUPERVISOR"},
    }


def comparison() -> dict:
    return {"comparison_sha256": SHA}


RECEIPT_MUTATIONS = [
    ("schema_version", "haxs.stage5c2gR32A1.authorization.v1"),
    ("decision", "REJECT"), ("candidate_sha256", OTHER),
    ("protocol_archive_sha256", OTHER), ("runtime_tree_sha256", OTHER),
    ("wheel_sha256", OTHER), ("environment_sha256", OTHER),
    ("g1_config_sha256", OTHER), ("g1_plan_sha256", OTHER),
    ("unit_registry_sha256", OTHER), ("runner_sha256", OTHER),
    ("test_ledger_sha256", OTHER), ("g0_return_sha256", OTHER),
    ("two_host_g0_sha256", OTHER), ("authorized_scope", "G1_G2"),
    ("blocked_scopes", BLOCKED_SCOPES[:-1]), ("receipt_id", "not-a-uuid"),
    ("issued_at_utc", "2026-08-03T10:00:00"),
    ("issuer", {"name": "", "role": "SUPERVISOR"}),
    ("issuer", {"name": "Supervisor", "role": "STUDENT"}),
]


def test_valid_golden_receipt_schema_is_accepted() -> None:
    value = receipt()
    assert set(value) == RECEIPT_KEYS
    assert validate_receipt(value, candidate(), SHA, SHA, comparison()) == value


@pytest.mark.parametrize(("field", "value"), RECEIPT_MUTATIONS)
def test_fixed_invalid_receipts_fail_closed(field: str, value: object) -> None:
    invalid = receipt()
    invalid[field] = value
    with pytest.raises(RuntimeError):
        validate_receipt(invalid, candidate(), SHA, SHA, comparison())


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def host_fixture(root: Path, label: str, physical: str) -> Path:
    base = root / label
    junit = base / "junit"
    transcripts = base / "transcripts"
    junit.mkdir(parents=True)
    transcripts.mkdir()
    for name in ["full.xml", "targeted.xml"]:
        (junit / name).write_text('<testsuite tests="1" failures="0" errors="0"></testsuite>\n', encoding="utf-8")
    (transcripts / "run.txt").write_text("PASS\n", encoding="utf-8")
    ledger = {
        "schema_version": "haxs.stage5c2gR32A2.named-tests.v1",
        "suites": {"full": {"nodeids": ["tests/a.py::test_a"]}, "targeted": {"nodeids": ["tests/a.py::test_a"]}},
        "counts": {"full": 1, "targeted": 1}, "status": "PASS",
    }
    ledger["ledger_sha256"] = sha256_payload(ledger)
    _write_json(base / "ledger.json", ledger)
    primary = {
        "full_junit": {"path": f"{label}/junit/full.xml", "sha256": sha256_file(junit / "full.xml")},
        "targeted_junit": {"path": f"{label}/junit/targeted.xml", "sha256": sha256_file(junit / "targeted.xml")},
        "named_test_ledger": {"path": f"{label}/ledger.json", "sha256": sha256_file(base / "ledger.json")},
        "transcripts": [{"path": f"{label}/transcripts/run.txt", "sha256": sha256_file(transcripts / "run.txt")}],
    }
    record = {
        "schema_version": "haxs.stage5c2gR32A2.physical-host-g0.v1", "status": "PASS",
        "host_label": label, "candidate_sha256": SHA, "runtime_tree_sha256": SHA,
        "root_manifest_sha256": SHA, "wheel_sha256": SHA, "environment_sha256": SHA,
        "dependency_lock_sha256": SHA, "wheelhouse_manifest_sha256": SHA,
        "protocol_archive_sha256": SHA, "g1_config_sha256": SHA, "g1_plan_sha256": SHA,
        "unit_registry_sha256": SHA, "runner_sha256": SHA, "test_ledger_sha256": SHA,
        "adversarial_outcomes_sha256": SHA,
        "physical_host": {"system": "Darwin", "machine": "arm64", "platform_identity_sha256": physical, "serial_or_node_sha256": physical},
        "primary_evidence": primary, "test_counts": {"full": 1, "targeted": 1},
        "scientific_execution_performed": False, "G1_authorized": False,
        "prior_authorization_present": False,
    }
    path = root / f"{label}.json"
    _write_json(path, record)
    return path


def test_valid_primary_host_evidence_is_recomputed(tmp_path: Path) -> None:
    host_a = host_fixture(tmp_path, "HOST_A", "1" * 64)
    host_b = host_fixture(tmp_path, "HOST_B", "2" * 64)
    result = recompute_two_host_g0(host_a, host_b, tmp_path, candidate())
    assert result["status"] == "PASS"


def test_valid_complete_g0_fixture_only_dry_runs_and_creates_no_authorization(monkeypatch, tmp_path: Path) -> None:
    value = candidate()
    value.update({
        "schema_version": "haxs.stage5c2gR32A2.candidate.v1",
        "execution_permissions": {"G1": "BLOCKED_PENDING_NEW_SUPERVISORY_REVIEW_AND_RECEIPT"},
    })
    value["candidate_sha256"] = sha256_payload({key: item for key, item in value.items() if key != "candidate_sha256"})
    candidate_path = tmp_path / "results/stage5c2gR32A2/protocol/CANDIDATE.json"
    _write_json(candidate_path, value)
    protocol = tmp_path / "protocol.zip"
    protocol.write_bytes(b"golden protocol fixture")
    protocol_sha = sha256_file(protocol)
    return_root = tmp_path / "complete_return"
    return_root.mkdir()
    host_a_path = host_fixture(return_root, "HOST_A", "1" * 64)
    host_b_path = host_fixture(return_root, "HOST_B", "2" * 64)
    for path in [host_a_path, host_b_path]:
        host = json.loads(path.read_text(encoding="utf-8"))
        host["candidate_sha256"] = value["candidate_sha256"]
        host["protocol_archive_sha256"] = protocol_sha
        _write_json(path, host)
    recomputed = finalize_comparison(recompute_two_host_g0(host_a_path, host_b_path, return_root, value))
    comparison_path = return_root / "TWO_HOST_G0.json"
    _write_json(comparison_path, recomputed)
    files = {
        path.relative_to(return_root).as_posix(): sha256_file(path)
        for path in sorted(return_root.rglob("*")) if path.is_file()
    }
    return_record = {
        "schema_version": "haxs.stage5c2gR32A2.complete-g0-return.v1",
        "candidate_sha256": value["candidate_sha256"], "protocol_archive_sha256": protocol_sha,
        "host_a_path": "HOST_A.json", "host_b_path": "HOST_B.json",
        "comparison_path": "TWO_HOST_G0.json", "files": files,
        "scientific_execution_performed": False, "G1_authorized": False,
        "return_sha256": "",
    }
    return_record["return_sha256"] = sha256_payload({key: item for key, item in return_record.items() if key != "return_sha256"})
    _write_json(return_root / "G0_RETURN.json", return_record)
    structured = receipt()
    structured.update({
        "candidate_sha256": value["candidate_sha256"],
        "protocol_archive_sha256": protocol_sha,
        "g0_return_sha256": return_record["return_sha256"],
        "two_host_g0_sha256": recomputed["comparison_sha256"],
    })
    receipt_path = tmp_path / "receipt.json"
    _write_json(receipt_path, structured)
    monkeypatch.setattr(finalizer, "verify_protocol", lambda path: {"candidate_sha256": value["candidate_sha256"]})
    result = finalizer.authorize(receipt_path, protocol, return_root, True, tmp_path)
    assert result["status"] == "VALIDATED_DRY_RUN"
    for relative in [AUTHORIZATION_PATH, LOCK_PATH, RECEIPT_PATH, STATE_PATH]:
        assert not (tmp_path / relative.relative_to(ROOT)).exists()


HOST_MUTATIONS = [
    "altered_runtime", "altered_environment", "equal_physical", "missing_full_junit",
    "altered_targeted_junit", "missing_ledger", "altered_ledger", "missing_transcript",
    "wrong_candidate", "scientific_execution", "g1_authorized", "prior_authorization",
]


@pytest.mark.parametrize("mutation", HOST_MUTATIONS)
def test_invalid_primary_host_evidence_cannot_be_hidden_by_a_forged_comparator(tmp_path: Path, mutation: str) -> None:
    host_a_path = host_fixture(tmp_path, "HOST_A", "1" * 64)
    host_b_path = host_fixture(tmp_path, "HOST_B", "2" * 64)
    host_b = json.loads(host_b_path.read_text(encoding="utf-8"))
    if mutation == "altered_runtime": host_b["runtime_tree_sha256"] = OTHER
    elif mutation == "altered_environment": host_b["environment_sha256"] = OTHER
    elif mutation == "equal_physical": host_b["physical_host"] = json.loads(host_a_path.read_text())["physical_host"]
    elif mutation == "wrong_candidate": host_b["candidate_sha256"] = OTHER
    elif mutation == "scientific_execution": host_b["scientific_execution_performed"] = True
    elif mutation == "g1_authorized": host_b["G1_authorized"] = True
    elif mutation == "prior_authorization": host_b["prior_authorization_present"] = True
    elif mutation == "missing_full_junit": (tmp_path / host_b["primary_evidence"]["full_junit"]["path"]).unlink()
    elif mutation == "altered_targeted_junit": (tmp_path / host_b["primary_evidence"]["targeted_junit"]["path"]).write_text("altered")
    elif mutation == "missing_ledger": (tmp_path / host_b["primary_evidence"]["named_test_ledger"]["path"]).unlink()
    elif mutation == "altered_ledger": (tmp_path / host_b["primary_evidence"]["named_test_ledger"]["path"]).write_text("{}")
    elif mutation == "missing_transcript": (tmp_path / host_b["primary_evidence"]["transcripts"][0]["path"]).unlink()
    _write_json(host_b_path, host_b)
    with pytest.raises(RuntimeError):
        recompute_two_host_g0(host_a_path, host_b_path, tmp_path, candidate())


@pytest.mark.parametrize("relative", [
    "scripts/yaml.pyc", "site/injected.pth", "payload.zip", "native/injected.so",
    "conftest.py", "sitecustomize.py", "usercustomize.py",
])
def test_import_channels_are_rejected_when_unlisted(relative: str) -> None:
    with pytest.raises(RuntimeError):
        assert_exact_membership({"bound.py": SHA, relative: SHA}, {"bound.py": SHA})
    if relative.endswith((".pyc", ".pth")) or Path(relative).name in {"conftest.py", "sitecustomize.py", "usercustomize.py"}:
        with pytest.raises(RuntimeError):
            assert_no_forbidden_import_artifacts({relative: SHA})


@pytest.mark.parametrize("failure", ["wrong_python", "wrong_dependency", "wrong_shared_library", "wheel_install_failure"])
def test_setup_failure_does_not_reserve_scientific_attempt(tmp_path: Path, failure: str) -> None:
    launcher = tmp_path / "scripts/launch_stage5c2gR32A2_G1_isolated.py"
    launcher.parent.mkdir(parents=True)
    launcher.write_text("fixture\n", encoding="utf-8")
    value = candidate()
    value["authorization_contract"]["launcher"]["sha256"] = sha256_file(launcher)
    authorization = {"receipt": {"receipt_id": "fixture"}}
    def environment_failure(*args, **kwargs):
        raise RuntimeError(failure)
    with pytest.raises(RuntimeError, match=failure):
        preflight_and_reserve(
            value, authorization, tmp_path,
            root_verifier=lambda *args: {"status": "PASS"},
            environment_verifier=environment_failure,
        )
    assert not (tmp_path / STATE_PATH.relative_to(ROOT)).exists()
    assert not (tmp_path / SETUP_STATE_PATH.relative_to(ROOT)).exists()
    assert not (tmp_path / AUTHORIZATION_PATH.relative_to(ROOT)).exists()
    assert not (tmp_path / LOCK_PATH.relative_to(ROOT)).exists()
    assert not (tmp_path / RECEIPT_PATH.relative_to(ROOT)).exists()


def test_fixture_ledger_contains_at_least_twenty_fixed_invalid_cases() -> None:
    ledger = json.loads((ROOT / "configs/stage5c2gR32A2/adversarial_fixture_ledger.json").read_text())
    assert len(ledger["invalid_fixtures"]) >= 20
    assert ledger["required_outcome"] == "FAIL_BEFORE_RECEIPT_LOCK_OR_SCIENTIFIC_STATE"


def _installed_wheel_fixture(target: Path, wheel: Path, source_url: str) -> None:
    members = {
        "haxs/__init__.py": b'__version__ = "0.8.5"\n',
        "haxs-0.8.5.dist-info/METADATA": b"Name: haxs\nVersion: 0.8.5\n",
        "haxs-0.8.5.dist-info/WHEEL": b"Wheel-Version: 1.0\nRoot-Is-Purelib: true\n",
    }
    if not wheel.exists():
        with zipfile.ZipFile(wheel, "w") as archive:
            for name, content in members.items():
                archive.writestr(name, content)
            archive.writestr("haxs-0.8.5.dist-info/RECORD", b"")
    for name, content in members.items():
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    dist = target / "haxs-0.8.5.dist-info"
    (dist / "INSTALLER").write_text("pip\n", encoding="utf-8")
    (dist / "REQUESTED").write_text("", encoding="utf-8")
    wheel_sha = sha256_file(wheel)
    (dist / "direct_url.json").write_text(json.dumps({
        "archive_info": {"hashes": {"sha256": wheel_sha}}, "url": source_url,
    }), encoding="utf-8")
    rows = []
    for name, content in members.items():
        encoded = base64.urlsafe_b64encode(hashlib.sha256(content).digest()).decode().rstrip("=")
        rows.append(f"{name},sha256={encoded},{len(content)}")
    rows.extend([
        "haxs-0.8.5.dist-info/INSTALLER,,",
        "haxs-0.8.5.dist-info/REQUESTED,,",
        "haxs-0.8.5.dist-info/direct_url.json,,",
        "haxs-0.8.5.dist-info/RECORD,,",
    ])
    (dist / "RECORD").write_text("\n".join(rows) + "\n", encoding="utf-8")


def test_installed_wheel_payload_identity_ignores_only_absolute_source_url(tmp_path: Path) -> None:
    wheel = tmp_path / "haxs-0.8.5-py3-none-any.whl"
    first = tmp_path / "first/site"
    second = tmp_path / "second/site"
    _installed_wheel_fixture(first, wheel, "file:///first/absolute/location/haxs.whl")
    _installed_wheel_fixture(second, wheel, "file:///different/absolute/location/haxs.whl")
    first_identity = installed_wheel_tree_identity(first, wheel)
    second_identity = installed_wheel_tree_identity(second, wheel)
    assert first_identity["payload_tree_sha256"] == second_identity["payload_tree_sha256"]
    assert first_identity["generated_metadata_policy"] == second_identity["generated_metadata_policy"]
    (second / "haxs/__init__.py").write_text("altered\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="payload differs"):
        installed_wheel_tree_identity(second, wheel)
