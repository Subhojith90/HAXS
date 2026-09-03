from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from run_stage5c2gR32A4_g0 import run_recorded
from stage5c2gR32A4_common import sha256_file
from stage5c2gR32A4_semantics import (
    canonical_junit_target, normalized_argv, verify_command_record,
)

NODEID = "tests/stage5c2gR32A4/fixtures/golden_case.py::test_writer_roundtrip"


def _production_record(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path, dict]:
    evidence = (tmp_path / "moved root with spaces" / "evidence").resolve()
    stdout = evidence / "HOST_A_stdout/full_tests.txt"
    record = evidence / "HOST_A_command_records/full_tests.json"
    junit = evidence / "HOST_A_junit/full_tests.xml"
    for parent in [stdout.parent, record.parent, junit.parent]:
        parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HAXS_R32A4_G0_PYCACHE", str(tmp_path / "external-pycache"))
    command = [
        sys.executable, "-I", "-B", "-m", "pytest", "-q", "-p",
        "no:cacheprovider", f"--junitxml={junit}", NODEID,
    ]
    produced = run_recorded(
        command, "full_tests", evidence, stdout, record, 1,
        sha256_file(Path(sys.executable)), junit, [NODEID],
    )
    return evidence, record, produced


def test_production_writer_record_round_trips_under_safe_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    evidence, record, produced = _production_record(tmp_path, monkeypatch)
    verified = verify_command_record(
        record, evidence, "full_tests", produced["argv_template"], 1,
        sha256_file(Path(sys.executable)), produced["junit"],
    )
    assert verified["record_sha256"] == produced["record_sha256"]


def test_production_record_remains_verifiable_after_evidence_is_moved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    evidence, _, produced = _production_record(tmp_path, monkeypatch)
    moved = (tmp_path / "relocated evidence ü").resolve()
    shutil.move(str(evidence), moved)
    record = moved / "HOST_A_command_records/full_tests.json"
    verified = verify_command_record(
        record, moved, "full_tests", produced["argv_template"], 1,
        sha256_file(Path(sys.executable)),
        {"path": "HOST_A_junit/full_tests.xml", "sha256": produced["junit"]["sha256"]},
    )
    assert verified["exit_status"] == 0


@pytest.mark.parametrize(
    "mutation",
    ["missing", "duplicate", "malformed", "empty", "outside", "wrong-root", "missing-output", "noncanonical"],
)
def test_junit_target_mutations_fail_closed(tmp_path: Path, mutation: str) -> None:
    root = (tmp_path / "evidence").resolve()
    target = root / "HOST_A_junit/full_tests.xml"
    target.parent.mkdir(parents=True)
    target.write_text("<testsuite tests='0'/>", encoding="utf-8")
    argv = [sys.executable, f"--junitxml={target}"]
    recorded = "HOST_A_junit/full_tests.xml"
    execution_root = str(root)
    if mutation == "missing":
        argv = [sys.executable]
    elif mutation == "duplicate":
        argv.append(f"--junitxml={target}")
    elif mutation == "malformed":
        argv = [sys.executable, "--junitxml", str(target)]
    elif mutation == "empty":
        argv = [sys.executable, "--junitxml="]
    elif mutation == "outside":
        argv = [sys.executable, f"--junitxml={tmp_path / 'outside.xml'}"]
    elif mutation == "wrong-root":
        execution_root = str((tmp_path / "other").resolve())
    elif mutation == "missing-output":
        target.unlink()
    elif mutation == "noncanonical":
        argv = [sys.executable, f"--junitxml={root / 'HOST_A_junit/../HOST_A_junit/full_tests.xml'}"]
    with pytest.raises(RuntimeError):
        canonical_junit_target(argv, root, recorded, execution_root)


def test_relative_argv_target_is_equivalent_to_recorded_relative_path(tmp_path: Path) -> None:
    root = (tmp_path / "evidence").resolve()
    target = root / "HOST_A_junit/full_tests.xml"
    target.parent.mkdir(parents=True)
    target.write_text("<testsuite tests='0'/>", encoding="utf-8")
    actual, normalized = canonical_junit_target(
        [sys.executable, "--junitxml=HOST_A_junit/full_tests.xml"],
        root, "HOST_A_junit/full_tests.xml", str(root),
    )
    assert actual == target
    assert normalized[-1] == "--junitxml={JUNIT}"


def test_symlinked_junit_target_and_ancestor_fail_closed(tmp_path: Path) -> None:
    root = (tmp_path / "evidence").resolve()
    real = tmp_path / "real.xml"
    real.write_text("<testsuite tests='0'/>", encoding="utf-8")
    direct = root / "HOST_A_junit/full_tests.xml"
    direct.parent.mkdir(parents=True)
    direct.symlink_to(real)
    with pytest.raises(RuntimeError):
        canonical_junit_target(
            [sys.executable, f"--junitxml={direct}"], root,
            "HOST_A_junit/full_tests.xml", str(root),
        )
    direct.unlink()
    direct.parent.rmdir()
    (root / "HOST_A_junit").symlink_to(tmp_path)
    with pytest.raises(RuntimeError):
        canonical_junit_target(
            [sys.executable, f"--junitxml={root / 'HOST_A_junit/real.xml'}"], root,
            "HOST_A_junit/real.xml", str(root),
        )


def test_compileall_external_pycache_prefix_is_canonicalized(tmp_path: Path) -> None:
    evidence_roots = [
        (tmp_path / "synthetic_hosts/HOST_A").resolve(),
        (tmp_path / "physical_run/evidence").resolve(),
    ]
    for evidence in evidence_roots:
        evidence.mkdir(parents=True)
        pycache = evidence.parent / "diagnostics/HOST_A_external_pycache"
        argv = [
            sys.executable, "-I", "-B", "-X", f"pycache_prefix={pycache}",
            "-m", "compileall", "-q", "src", "scripts", "scripts_patch", "tests",
        ]
        normalized = normalized_argv(argv, evidence, None, str(evidence))
        assert normalized[4] == "pycache_prefix={PYCACHE}"


def test_compileall_wrong_pycache_prefix_fails_closed(tmp_path: Path) -> None:
    evidence = (tmp_path / "synthetic_hosts/HOST_A").resolve()
    evidence.mkdir(parents=True)
    argv = [
        sys.executable, "-I", "-B", "-X",
        f"pycache_prefix={tmp_path / 'unbound-cache'}",
        "-m", "compileall", "-q", "src", "scripts", "scripts_patch", "tests",
    ]
    with pytest.raises(RuntimeError, match="pycache prefix differs"):
        normalized_argv(argv, evidence, None, str(evidence))


def test_isolated_compileall_writes_only_to_external_pycache(tmp_path: Path) -> None:
    execution = tmp_path / "execution"
    source = execution / "src/probe.py"
    source.parent.mkdir(parents=True)
    source.write_text("VALUE = 1\n", encoding="utf-8")
    external = tmp_path / "diagnostics/HOST_A_external_pycache"
    completed = subprocess.run(
        [
            sys.executable, "-I", "-B", "-X", f"pycache_prefix={external}",
            "-m", "compileall", "-q", "src",
        ],
        cwd=execution, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    assert completed.returncode == 0, completed.stdout
    assert not list(execution.rglob("*.pyc"))
    assert list(external.rglob("*.pyc"))
