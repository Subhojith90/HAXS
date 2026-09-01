from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

from stage5c2gR32A2_common import safe_relative, sha256_file, sha256_payload, strict_json

JUNIT_SCHEMA = "haxs.stage5c2gR32A5.junit-semantics.v1"
COMMAND_SCHEMA = "haxs.stage5c2gR32A5.command-record.v1"
JUNIT_PLACEHOLDER = "--junitxml={JUNIT}"
PYCACHE_PLACEHOLDER = "pycache_prefix={PYCACHE}"


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


def _absolute_lexical(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def canonical_junit_target(
    argv: list[str], evidence_root: Path, recorded_relative_path: str,
    execution_evidence_root: str,
) -> tuple[Path, list[str]]:
    """Bind one production ``--junitxml=`` argument to its evidence record.

    The recorded form is always relative to the evidence root.  The executed
    command may carry that relative target or its absolute equivalent, but no
    other spelling or filesystem object is accepted.
    """
    if not isinstance(argv, list) or not argv or any(
        not isinstance(item, str) or not item for item in argv
    ):
        raise RuntimeError("structured command argv is invalid")
    root = _absolute_lexical(evidence_root)
    if not root.is_dir() or root.is_symlink() or root.resolve(strict=True) != root:
        raise RuntimeError("canonical evidence root is missing, symlinked, or noncanonical")
    relative = safe_relative(recorded_relative_path)
    recorded = root / relative
    execution_root = Path(execution_evidence_root)
    if (
        not execution_root.is_absolute()
        or any(part in {"", ".", ".."} for part in execution_root.parts)
        or _absolute_lexical(execution_root) != execution_root
    ):
        raise RuntimeError("recorded execution evidence root is not canonical and absolute")
    matches = [item for item in argv if item.startswith("--junitxml")]
    if len(matches) != 1 or not matches[0].startswith("--junitxml="):
        raise RuntimeError("structured command must contain exactly one --junitxml= target")
    raw_value = matches[0].split("=", 1)[1]
    if not raw_value:
        raise RuntimeError("structured command JUnit target is empty")
    raw = Path(raw_value)
    if any(part in {"", ".", ".."} for part in raw.parts):
        raise RuntimeError("structured command JUnit target is noncanonical")
    expected_executed = execution_root / relative
    actual = _absolute_lexical(raw if raw.is_absolute() else execution_root / raw)
    if actual != expected_executed:
        raise RuntimeError("structured command JUnit target differs from its recorded path")
    try:
        expected_executed.relative_to(execution_root)
    except ValueError as error:
        raise RuntimeError("structured command JUnit target escapes the evidence root") from error
    current = root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise RuntimeError("structured command JUnit target or ancestor is symlinked")
    if not recorded.is_file() or recorded.resolve(strict=True) != recorded:
        raise RuntimeError("structured command JUnit target is missing or noncanonical")
    normalized = ["{BOUND_PYTHON}", *argv[1:]]
    normalized[normalized.index(matches[0])] = JUNIT_PLACEHOLDER
    return actual, normalized


def normalized_argv(
    argv: list[str], evidence_root: Path, junit_path: str | None,
    execution_evidence_root: str,
) -> list[str]:
    if not isinstance(argv, list) or not argv or any(not isinstance(item, str) or not item for item in argv):
        raise RuntimeError("structured command argv is invalid")
    if junit_path is None:
        if any(item.startswith("--junitxml") for item in argv):
            raise RuntimeError("non-JUnit command unexpectedly contains a JUnit target")
        normalized = ["{BOUND_PYTHON}", *argv[1:]]
    else:
        normalized = canonical_junit_target(
            argv, evidence_root, junit_path, execution_evidence_root
        )[1]
    matches = [
        (index, item) for index, item in enumerate(normalized)
        if item.startswith("pycache_prefix=")
    ]
    if len(matches) > 1:
        raise RuntimeError("structured command contains duplicate pycache prefixes")
    if matches:
        index, item = matches[0]
        if index == 0 or normalized[index - 1] != "-X":
            raise RuntimeError("structured command pycache prefix lacks canonical -X form")
        execution_root = Path(execution_evidence_root)
        if (
            not execution_root.is_absolute()
            or any(part in {"", ".", ".."} for part in execution_root.parts)
            or _absolute_lexical(execution_root) != execution_root
        ):
            raise RuntimeError("recorded execution evidence root is not canonical and absolute")
        raw = item.split("=", 1)[1]
        if not raw:
            raise RuntimeError("structured command pycache prefix is empty")
        actual = _absolute_lexical(Path(raw))
        expected_parent = execution_root.parent / "diagnostics"
        if (
            actual.parent != expected_parent
            or actual.name not in {
                "HOST_A_external_pycache", "HOST_B_external_pycache",
            }
        ):
            raise RuntimeError("structured command pycache prefix differs from the isolated external target")
        normalized[index] = PYCACHE_PLACEHOLDER
    return normalized


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
        "execution_evidence_root", "record_sha256",
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
    if normalized_argv(
        record["argv"], evidence_root, junit_path, record["execution_evidence_root"]
    ) != expected_argv_template:
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
