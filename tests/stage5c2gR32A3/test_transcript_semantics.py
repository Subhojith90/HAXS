from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2gR32A2_common import sha256_file, sha256_payload
from stage5c2gR32A3_semantics import COMMAND_SCHEMA, verify_command_record

SHA = "a" * 64


def fixture(tmp_path: Path) -> tuple[Path, dict, list[str]]:
    stdout = tmp_path / "stdout.txt"
    stdout.write_text("1 passed\n", encoding="utf-8")
    junit = tmp_path / "result.xml"
    junit.write_text("<testsuite tests='1' failures='0' errors='0' skipped='0'/>", encoding="utf-8")
    junit_record = {"path": "result.xml", "sha256": sha256_file(junit)}
    argv = ["/bound/python", "-I", "-B", "-m", "pytest", "--junitxml=/tmp/result.xml", "tests/a.py::test_a"]
    template = ["{BOUND_PYTHON}", "-I", "-B", "-m", "pytest", "--junitxml={JUNIT}", "tests/a.py::test_a"]
    record = {
        "schema_version": COMMAND_SCHEMA, "stage": "full_tests", "status": "PASS",
        "argv": argv, "argv_template": template, "python_executable_sha256": SHA,
        "started_at_utc": "2026-08-06T00:00:00Z", "ended_at_utc": "2026-08-06T00:00:01Z",
        "exit_status": 0, "expected_test_count": 1, "observed_test_count": 1,
        "summary": {"tests": 1, "failures": 0, "errors": 0, "skipped": 0},
        "stdout": {"path": "stdout.txt", "sha256": sha256_file(stdout)},
        "junit": {"path": "/tmp/result.xml", "sha256": junit_record["sha256"]},
    }
    record["record_sha256"] = sha256_payload(record)
    path = tmp_path / "record.json"
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path, record["junit"], template


def rewrite(path: Path, **changes: object) -> None:
    record = json.loads(path.read_text())
    record.update(changes)
    record["record_sha256"] = sha256_payload({key: value for key, value in record.items() if key != "record_sha256"})
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def test_exact_structured_command_record_is_accepted(tmp_path: Path) -> None:
    path, junit, template = fixture(tmp_path)
    assert verify_command_record(path, tmp_path, "full_tests", template, 1, SHA, junit)["exit_status"] == 0


@pytest.mark.parametrize("field,value", [
    ("exit_status", 17), ("status", "PASS"), ("observed_test_count", 0),
    ("expected_test_count", 2), ("python_executable_sha256", "b" * 64),
])
def test_altered_command_exit_or_count_fails_closed(tmp_path: Path, field: str, value: object) -> None:
    path, junit, template = fixture(tmp_path)
    if field == "status":
        rewrite(path, status="FAILED")
    else:
        rewrite(path, **{field: value})
    with pytest.raises(RuntimeError):
        verify_command_record(path, tmp_path, "full_tests", template, 1, SHA, junit)


def test_wrong_argv_and_wrong_junit_binding_fail_closed(tmp_path: Path) -> None:
    path, junit, template = fixture(tmp_path)
    record = json.loads(path.read_text())
    record["argv"][-1] = "tests/unrelated.py::test_other"
    rewrite(path, argv=record["argv"])
    with pytest.raises(RuntimeError):
        verify_command_record(path, tmp_path, "full_tests", template, 1, SHA, junit)
