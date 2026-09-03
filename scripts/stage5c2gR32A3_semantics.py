from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

from stage5c2gR32A2_common import safe_relative, sha256_file, sha256_payload, strict_json

JUNIT_SCHEMA = "haxs.stage5c2gR32A3.junit-semantics.v1"
COMMAND_SCHEMA = "haxs.stage5c2gR32A3.command-record.v1"


def _expected_junit_pair(nodeid: str) -> tuple[str, str]:
    parts = nodeid.split("::")
    if len(parts) < 2 or not parts[0].startswith("tests/") or not parts[0].endswith(".py"):
        raise RuntimeError(f"non-canonical pytest node identifier: {nodeid!r}")
    module = parts[0][:-3].replace("/", ".")
    classname = ".".join([module, *parts[1:-1]]) if len(parts) > 2 else module
    return classname, parts[-1]


def verify_junit_semantics(path: Path, expected_nodeids: list[str]) -> dict:
    if len(expected_nodeids) != len(set(expected_nodeids)):
        raise RuntimeError("candidate-bound node-id ledger contains duplicates")
    try:
        root = ElementTree.parse(path).getroot()
    except (ElementTree.ParseError, OSError) as error:
        raise RuntimeError(f"invalid JUnit XML: {path}") from error
    if root.tag not in {"testsuite", "testsuites"}:
        raise RuntimeError(f"unexpected JUnit root element: {root.tag}")
    cases = list(root.iter("testcase"))
    observed_pairs: list[tuple[str, str]] = []
    failures = errors = skipped = 0
    for case in cases:
        classname = case.attrib.get("classname")
        name = case.attrib.get("name")
        if not classname or not name:
            raise RuntimeError("JUnit testcase lacks classname or name")
        observed_pairs.append((classname, name))
        failures += len(case.findall("failure"))
        errors += len(case.findall("error"))
        skipped += len(case.findall("skipped"))
    expected_pairs = [_expected_junit_pair(nodeid) for nodeid in expected_nodeids]
    if observed_pairs != expected_pairs:
        first = next(
            (index for index, pair in enumerate(zip(observed_pairs, expected_pairs)) if pair[0] != pair[1]),
            min(len(observed_pairs), len(expected_pairs)),
        )
        raise RuntimeError(
            "JUnit testcase identity/order/multiplicity failed: "
            f"observed={len(observed_pairs)} expected={len(expected_pairs)} first_difference={first}"
        )
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    declared_tests = sum(int(suite.attrib.get("tests", "0")) for suite in suites)
    declared_failures = sum(int(suite.attrib.get("failures", "0")) for suite in suites)
    declared_errors = sum(int(suite.attrib.get("errors", "0")) for suite in suites)
    declared_skipped = sum(int(suite.attrib.get("skipped", "0")) for suite in suites)
    if (
        declared_tests != len(expected_nodeids)
        or declared_failures != failures
        or declared_errors != errors
        or declared_skipped != skipped
        or failures
        or errors
        or skipped
    ):
        raise RuntimeError(
            "JUnit outcome semantics failed: "
            f"tests={declared_tests} failures={failures} errors={errors} skipped={skipped}"
        )
    result = {
        "schema_version": JUNIT_SCHEMA,
        "status": "PASS",
        "junit_sha256": sha256_file(path),
        "ordered_nodeids_sha256": sha256_payload(expected_nodeids),
        "tests": len(expected_nodeids),
        "failures": 0,
        "errors": 0,
        "skipped": 0,
    }
    result["semantics_sha256"] = sha256_payload(result)
    return result


def _utc(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise RuntimeError("structured command timestamp is invalid") from error
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise RuntimeError("structured command timestamp is not UTC")
    return parsed


def normalized_argv(argv: list[str], junit_path: str | None) -> list[str]:
    if not isinstance(argv, list) or not argv or any(not isinstance(item, str) or not item for item in argv):
        raise RuntimeError("structured command argv is invalid")
    result = ["{BOUND_PYTHON}", *argv[1:]]
    if junit_path is not None:
        marker = f"--junitxml={junit_path}"
        result = ["--junitxml={JUNIT}" if item == marker else item for item in result]
    return result


def verify_command_record(
    path: Path,
    evidence_root: Path,
    expected_stage: str,
    expected_argv_template: list[str],
    expected_count: int,
    expected_python_sha256: str,
    junit_record: dict | None,
) -> dict:
    record = strict_json(path)
    required = {
        "schema_version", "stage", "status", "argv", "argv_template",
        "python_executable_sha256", "started_at_utc", "ended_at_utc", "exit_status",
        "expected_test_count", "observed_test_count", "summary", "stdout", "junit",
        "record_sha256",
    }
    if set(record) != required:
        raise RuntimeError(f"{expected_stage} command-record schema failed")
    canonical = {key: value for key, value in record.items() if key != "record_sha256"}
    if record["record_sha256"] != sha256_payload(canonical):
        raise RuntimeError(f"{expected_stage} command-record self-identity failed")
    if (
        record["schema_version"] != COMMAND_SCHEMA
        or record["stage"] != expected_stage
        or record["status"] != "PASS"
        or record["exit_status"] != 0
        or record["expected_test_count"] != expected_count
        or record["observed_test_count"] != expected_count
        or record["python_executable_sha256"] != expected_python_sha256
        or record["argv_template"] != expected_argv_template
    ):
        raise RuntimeError(f"{expected_stage} command/exit/count semantics failed")
    junit_path = record["junit"]["path"] if isinstance(record["junit"], dict) else None
    if normalized_argv(record["argv"], junit_path) != expected_argv_template:
        raise RuntimeError(f"{expected_stage} actual argv differs from the frozen template")
    if _utc(record["ended_at_utc"]) < _utc(record["started_at_utc"]):
        raise RuntimeError(f"{expected_stage} command timestamps are reversed")
    summary = record["summary"]
    if summary != {"tests": expected_count, "failures": 0, "errors": 0, "skipped": 0}:
        raise RuntimeError(f"{expected_stage} structured summary failed")
    stdout = record["stdout"]
    if set(stdout) != {"path", "sha256"}:
        raise RuntimeError(f"{expected_stage} stdout binding schema failed")
    stdout_path = evidence_root / safe_relative(stdout["path"])
    if not stdout_path.is_file() or stdout_path.is_symlink() or sha256_file(stdout_path) != stdout["sha256"]:
        raise RuntimeError(f"{expected_stage} stdout identity failed")
    if junit_record is None:
        if record["junit"] is not None:
            raise RuntimeError(f"{expected_stage} unexpectedly claims JUnit evidence")
    else:
        if record["junit"] != junit_record:
            raise RuntimeError(f"{expected_stage} transcript-to-JUnit binding failed")
    return record
