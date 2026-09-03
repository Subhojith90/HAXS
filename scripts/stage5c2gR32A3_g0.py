from __future__ import annotations

from pathlib import Path

from stage5c2gR32A2_common import safe_relative, sha256_file, sha256_payload, strict_json
from stage5c2gR32A3_semantics import verify_command_record, verify_junit_semantics

IDENTITY_FIELDS = [
    "candidate_sha256", "runtime_tree_sha256", "root_manifest_sha256",
    "wheel_sha256", "environment_sha256", "dependency_lock_sha256",
    "wheelhouse_manifest_sha256", "protocol_archive_sha256", "g1_config_sha256",
    "g1_plan_sha256", "unit_registry_sha256", "runner_sha256",
    "test_ledger_sha256", "adversarial_outcomes_sha256",
]


def _bound_file(evidence_root: Path, record: dict, label: str) -> Path:
    if set(record) != {"path", "sha256"}:
        raise RuntimeError(f"{label} bound-file schema failed")
    path = evidence_root / safe_relative(record["path"])
    if not path.is_file() or path.is_symlink() or sha256_file(path) != record["sha256"]:
        raise RuntimeError(f"{label} bound-file identity failed")
    return path


def _pytest_template(nodeids: list[str]) -> list[str]:
    return [
        "{BOUND_PYTHON}", "-I", "-B", "-m", "pytest", "-q", "-p",
        "no:cacheprovider", "--junitxml={JUNIT}", *nodeids,
    ]


def verify_host_record(
    path: Path,
    evidence_root: Path,
    candidate: dict,
    label: str,
    actual_protocol_sha256: str,
) -> tuple[dict, dict]:
    host = strict_json(path)
    required = {
        "schema_version", "status", "host_label", *IDENTITY_FIELDS,
        "physical_host", "primary_evidence", "test_counts", "semantic_evidence",
        "scientific_execution_performed", "G1_authorized", "prior_authorization_present",
    }
    if set(host) != required:
        raise RuntimeError(f"{label} host record keys differ from the R3.2A.3 schema")
    if (
        host["schema_version"] != "haxs.stage5c2gR32A3.physical-host-g0.v1"
        or host["status"] != "PASS"
        or host["host_label"] != label
        or host["candidate_sha256"] != candidate["candidate_sha256"]
        or host["protocol_archive_sha256"] != actual_protocol_sha256
        or host["scientific_execution_performed"] is not False
        or host["G1_authorized"] is not False
        or host["prior_authorization_present"] is not False
    ):
        raise RuntimeError(f"{label} current-stage or actual-protocol binding failed")
    contracts = candidate["authorization_contract"]
    expected_identities = {
        "runtime_tree_sha256": candidate["runtime_tree_sha256"],
        "root_manifest_sha256": contracts["root_manifest"]["sha256"],
        "wheel_sha256": candidate["wheel"]["sha256"],
        "environment_sha256": candidate["environment"]["sha256"],
        "dependency_lock_sha256": candidate["dependency_lock"]["sha256"],
        "wheelhouse_manifest_sha256": candidate["wheelhouse_manifest"]["sha256"],
        "g1_config_sha256": contracts["g1_config"]["sha256"],
        "g1_plan_sha256": contracts["g1_plan"]["sha256"],
        "unit_registry_sha256": contracts["unit_registry"]["sha256"],
        "runner_sha256": contracts["runner"]["sha256"],
        "test_ledger_sha256": contracts["test_ledger"]["sha256"],
        "adversarial_outcomes_sha256": contracts["adversarial_outcomes"]["sha256"],
    }
    failed = [field for field, expected in expected_identities.items() if host[field] != expected]
    if failed:
        raise RuntimeError(f"{label} candidate-bound identities failed: {failed}")
    if set(host["physical_host"]) != {
        "system", "machine", "platform_identity_sha256", "serial_or_node_sha256"
    }:
        raise RuntimeError(f"{label} physical-host schema failed")
    primary = host["primary_evidence"]
    if set(primary) != {"full_junit", "targeted_junit", "named_test_ledger", "command_records"}:
        raise RuntimeError(f"{label} primary-evidence schema failed")
    full_path = _bound_file(evidence_root, primary["full_junit"], f"{label} full JUnit")
    targeted_path = _bound_file(evidence_root, primary["targeted_junit"], f"{label} targeted JUnit")
    ledger_path = _bound_file(evidence_root, primary["named_test_ledger"], f"{label} ledger")
    ledger = strict_json(ledger_path)
    if (
        ledger.get("schema_version") != "haxs.stage5c2gR32A3.named-tests.v1"
        or ledger.get("status") != "PASS"
        or ledger.get("counts") != host["test_counts"]
        or ledger.get("ledger_sha256")
        != sha256_payload({key: value for key, value in ledger.items() if key != "ledger_sha256"})
    ):
        raise RuntimeError(f"{label} named-test ledger semantics failed")
    full_semantics = verify_junit_semantics(full_path, ledger["suites"]["full"]["nodeids"])
    targeted_semantics = verify_junit_semantics(targeted_path, ledger["suites"]["targeted"]["nodeids"])
    records = primary["command_records"]
    if set(records) != {"compileall", "full_tests", "targeted_tests"}:
        raise RuntimeError(f"{label} command-record set failed")
    record_paths = {
        name: _bound_file(evidence_root, record, f"{label} {name} command record")
        for name, record in records.items()
    }
    python_sha = candidate["python_executable_sha256"]
    compile_record = verify_command_record(
        record_paths["compileall"], evidence_root, "compileall",
        ["{BOUND_PYTHON}", "-I", "-B", "-m", "compileall", "-q", "src", "scripts", "scripts_patch", "tests"],
        0, python_sha, None,
    )
    full_record = verify_command_record(
        record_paths["full_tests"], evidence_root, "full_tests",
        _pytest_template(ledger["suites"]["full"]["nodeids"]),
        host["test_counts"]["full"], python_sha, primary["full_junit"],
    )
    targeted_record = verify_command_record(
        record_paths["targeted_tests"], evidence_root, "targeted_tests",
        _pytest_template(ledger["suites"]["targeted"]["nodeids"]),
        host["test_counts"]["targeted"], python_sha, primary["targeted_junit"],
    )
    semantics = {
        "full_junit": full_semantics,
        "targeted_junit": targeted_semantics,
        "command_record_sha256": {
            "compileall": compile_record["record_sha256"],
            "full_tests": full_record["record_sha256"],
            "targeted_tests": targeted_record["record_sha256"],
        },
        "actual_protocol_sha256": actual_protocol_sha256,
    }
    semantics["semantic_evidence_sha256"] = sha256_payload(semantics)
    if host["semantic_evidence"] != semantics:
        raise RuntimeError(f"{label} supplied semantic-evidence summary is stale or forged")
    return host, semantics


def recompute_two_host_g0(
    host_a_path: Path,
    host_b_path: Path,
    evidence_root: Path,
    candidate: dict,
    actual_protocol_sha256: str,
) -> dict:
    host_a, semantics_a = verify_host_record(
        host_a_path, evidence_root, candidate, "HOST_A", actual_protocol_sha256
    )
    host_b, semantics_b = verify_host_record(
        host_b_path, evidence_root, candidate, "HOST_B", actual_protocol_sha256
    )
    mismatches = [field for field in IDENTITY_FIELDS if host_a[field] != host_b[field]]
    physical_a, physical_b = host_a["physical_host"], host_b["physical_host"]
    distinct = (
        physical_a["platform_identity_sha256"] != physical_b["platform_identity_sha256"]
        and physical_a["serial_or_node_sha256"] != physical_b["serial_or_node_sha256"]
    )
    if mismatches or not distinct:
        raise RuntimeError(f"two-host G0 failed: mismatches={mismatches} distinct={distinct}")
    return {
        "schema_version": "haxs.stage5c2gR32A3.two-host-g0.v1",
        "status": "PASS",
        "candidate_sha256": candidate["candidate_sha256"],
        "actual_protocol_archive_sha256": actual_protocol_sha256,
        "host_a_sha256": sha256_file(host_a_path),
        "host_b_sha256": sha256_file(host_b_path),
        "host_a_semantic_evidence_sha256": semantics_a["semantic_evidence_sha256"],
        "host_b_semantic_evidence_sha256": semantics_b["semantic_evidence_sha256"],
        "physically_distinct": True,
        "identity_mismatches": [],
        "forbidden_state": [],
        "G1_authorized": False,
        "scientific_execution_performed": False,
        "comparison_sha256": "",
    }


def finalize_comparison(payload: dict) -> dict:
    result = dict(payload)
    result["comparison_sha256"] = sha256_payload(
        {key: value for key, value in result.items() if key != "comparison_sha256"}
    )
    return result
