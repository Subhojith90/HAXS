from __future__ import annotations

import json
from pathlib import Path
from xml.etree import ElementTree

from stage5c2gR32A2_common import safe_relative, sha256_file, sha256_payload, strict_json

IDENTITY_FIELDS = [
    "candidate_sha256",
    "runtime_tree_sha256",
    "root_manifest_sha256",
    "wheel_sha256",
    "environment_sha256",
    "dependency_lock_sha256",
    "wheelhouse_manifest_sha256",
    "protocol_archive_sha256",
    "g1_config_sha256",
    "g1_plan_sha256",
    "unit_registry_sha256",
    "runner_sha256",
    "test_ledger_sha256",
    "adversarial_outcomes_sha256",
]


def _verify_junit(path: Path, expected_tests: int) -> None:
    root = ElementTree.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    tests = sum(int(item.attrib.get("tests", "0")) for item in suites)
    failures = sum(int(item.attrib.get("failures", "0")) for item in suites)
    errors = sum(int(item.attrib.get("errors", "0")) for item in suites)
    if tests != expected_tests or failures or errors:
        raise RuntimeError(
            f"JUnit result failed: tests={tests} expected={expected_tests} failures={failures} errors={errors}"
        )


def verify_host_record(path: Path, evidence_root: Path, candidate: dict, label: str) -> dict:
    host = strict_json(path)
    required = {
        "schema_version", "status", "host_label", *IDENTITY_FIELDS,
        "physical_host", "primary_evidence", "test_counts",
        "scientific_execution_performed", "G1_authorized", "prior_authorization_present",
    }
    if set(host) != required:
        raise RuntimeError(f"{label} host record keys differ from the frozen schema")
    if (
        host["schema_version"] != "haxs.stage5c2gR32A2.physical-host-g0.v1"
        or host["status"] != "PASS"
        or host["host_label"] != label
        or host["candidate_sha256"] != candidate["candidate_sha256"]
        or host["scientific_execution_performed"] is not False
        or host["G1_authorized"] is not False
        or host["prior_authorization_present"] is not False
    ):
        raise RuntimeError(f"{label} is not valid current-stage G0 evidence")
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
    failed_identities = [
        field for field, expected in expected_identities.items() if host[field] != expected
    ]
    if failed_identities:
        raise RuntimeError(f"{label} candidate-bound identities failed: {failed_identities}")
    if set(host["physical_host"]) != {
        "system", "machine", "platform_identity_sha256", "serial_or_node_sha256"
    }:
        raise RuntimeError(f"{label} physical-host schema failed")
    if set(host["primary_evidence"]) != {
        "full_junit", "targeted_junit", "named_test_ledger", "transcripts"
    }:
        raise RuntimeError(f"{label} primary-evidence schema failed")
    if set(host["test_counts"]) != {"full", "targeted"}:
        raise RuntimeError(f"{label} test-count schema failed")

    referenced: set[str] = set()
    for name in ["full_junit", "targeted_junit", "named_test_ledger"]:
        record = host["primary_evidence"][name]
        if set(record) != {"path", "sha256"}:
            raise RuntimeError(f"{label} {name} record schema failed")
        relative = safe_relative(record["path"])
        evidence = evidence_root / relative
        if not evidence.is_file() or evidence.is_symlink() or sha256_file(evidence) != record["sha256"]:
            raise RuntimeError(f"{label} {name} evidence identity failed")
        referenced.add(relative.as_posix())
    transcripts = host["primary_evidence"]["transcripts"]
    if not isinstance(transcripts, list) or not transcripts:
        raise RuntimeError(f"{label} transcript ledger is empty")
    for record in transcripts:
        if set(record) != {"path", "sha256"}:
            raise RuntimeError(f"{label} transcript record schema failed")
        relative = safe_relative(record["path"])
        evidence = evidence_root / relative
        if not evidence.is_file() or evidence.is_symlink() or sha256_file(evidence) != record["sha256"]:
            raise RuntimeError(f"{label} transcript evidence identity failed")
        referenced.add(relative.as_posix())

    _verify_junit(
        evidence_root / safe_relative(host["primary_evidence"]["full_junit"]["path"]),
        int(host["test_counts"]["full"]),
    )
    _verify_junit(
        evidence_root / safe_relative(host["primary_evidence"]["targeted_junit"]["path"]),
        int(host["test_counts"]["targeted"]),
    )
    ledger = strict_json(
        evidence_root / safe_relative(host["primary_evidence"]["named_test_ledger"]["path"])
    )
    if (
        ledger.get("status") != "PASS"
        or ledger.get("counts") != host["test_counts"]
        or ledger.get("ledger_sha256")
        != sha256_payload({key: value for key, value in ledger.items() if key != "ledger_sha256"})
    ):
        raise RuntimeError(f"{label} named-test ledger semantics failed")
    return host


def recompute_two_host_g0(host_a_path: Path, host_b_path: Path, evidence_root: Path, candidate: dict) -> dict:
    host_a = verify_host_record(host_a_path, evidence_root, candidate, "HOST_A")
    host_b = verify_host_record(host_b_path, evidence_root, candidate, "HOST_B")
    mismatches = [field for field in IDENTITY_FIELDS if host_a[field] != host_b[field]]
    physical_a = host_a["physical_host"]
    physical_b = host_b["physical_host"]
    distinct = (
        physical_a["platform_identity_sha256"] != physical_b["platform_identity_sha256"]
        and physical_a["serial_or_node_sha256"] != physical_b["serial_or_node_sha256"]
    )
    if mismatches or not distinct:
        raise RuntimeError(f"two-host G0 failed: mismatches={mismatches} distinct={distinct}")
    return {
        "schema_version": "haxs.stage5c2gR32A2.two-host-g0.v1",
        "status": "PASS",
        "candidate_sha256": candidate["candidate_sha256"],
        "host_a_sha256": sha256_file(host_a_path),
        "host_b_sha256": sha256_file(host_b_path),
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
