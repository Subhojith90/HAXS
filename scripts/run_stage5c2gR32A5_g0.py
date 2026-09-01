#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2gR32A5_common import (
    load_candidate, sha256_file, sha256_payload, strict_json,
)
from stage5c2gR32A5_semantics import COMMAND_SCHEMA, normalized_argv, verify_junit_semantics
from verify_stage5c2gR32A5_environment import verify_environment
from verify_stage5c2gR32A5_fresh_unzip import verify_protocol
from verify_stage5c2gR32A5_root import verify_root


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def physical_identity() -> dict:
    output = subprocess.run(
        ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
        text=True, capture_output=True, check=True,
    ).stdout
    values = []
    for key in ["IOPlatformUUID", "IOPlatformSerialNumber"]:
        match = re.search(rf'"{key}"\s*=\s*"([^"]+)"', output)
        if not match:
            raise RuntimeError(f"physical host field unavailable: {key}")
        values.append(match.group(1))
    return {
        "system": platform.system(), "machine": platform.machine(),
        "platform_identity_sha256": hashlib.sha256(values[0].encode()).hexdigest(),
        "serial_or_node_sha256": hashlib.sha256(values[1].encode()).hexdigest(),
    }


def clean_environment() -> dict[str, str]:
    excluded = {
        "PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP", "PYTHONINSPECT", "PYTHONUSERBASE",
        "LD_PRELOAD", "DYLD_INSERT_LIBRARIES", "DYLD_LIBRARY_PATH",
    }
    environment = {key: value for key, value in os.environ.items() if key not in excluded}
    environment.update({
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPYCACHEPREFIX": os.environ["HAXS_R32A5_G0_PYCACHE"],
        "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
        "VECLIB_MAXIMUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1",
    })
    return environment


def run_recorded(
    command: list[str], stage: str, evidence_root: Path, stdout_path: Path,
    record_path: Path, expected_count: int, python_sha256: str,
    junit_path: Path | None, expected_nodeids: list[str] | None,
) -> dict:
    started = utc_now()
    completed = subprocess.run(
        command, cwd=ROOT, env=clean_environment(), text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    ended = utc_now()
    stdout_path.write_text(completed.stdout, encoding="utf-8")
    if completed.returncode:
        raise RuntimeError(f"G0 command failed before evidence acceptance: {stage}")
    if junit_path is None:
        observed = 0
        junit_record = None
        summary = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    else:
        if expected_nodeids is None:
            raise RuntimeError("JUnit command lacks an expected node-id ledger")
        semantic = verify_junit_semantics(junit_path, expected_nodeids)
        observed = semantic["tests"]
        junit_record = {
            "path": junit_path.relative_to(evidence_root).as_posix(),
            "sha256": sha256_file(junit_path),
        }
        summary = {
            "tests": semantic["tests"], "failures": semantic["failures"],
            "errors": semantic["errors"], "skipped": semantic["skipped"],
        }
    record = {
        "schema_version": COMMAND_SCHEMA,
        "stage": stage,
        "status": "PASS",
        "argv": command,
        "argv_template": normalized_argv(
            command, evidence_root,
            junit_record["path"] if junit_record is not None else None,
            str(evidence_root),
        ),
        "python_executable_sha256": python_sha256,
        "execution_evidence_root": str(evidence_root),
        "started_at_utc": started,
        "ended_at_utc": ended,
        "exit_status": completed.returncode,
        "expected_test_count": expected_count,
        "observed_test_count": observed,
        "summary": summary,
        "stdout": {
            "path": stdout_path.relative_to(evidence_root).as_posix(),
            "sha256": sha256_file(stdout_path),
        },
        "junit": junit_record,
    }
    record["record_sha256"] = sha256_payload(record)
    record_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host-label", choices=["HOST_A", "HOST_B"], required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if not sys.flags.isolated or sys.version_info[:3] != (3, 12, 7):
        raise RuntimeError("G0 requires isolated exact CPython 3.12.7")
    evidence_root = args.out.parent.resolve()
    if args.out.exists() or args.out.is_symlink() or evidence_root.exists():
        raise RuntimeError("G0 evidence root must not already exist")
    evidence_root.mkdir(parents=True)
    stdout_root = evidence_root / f"{args.host_label}_stdout"
    records_root = evidence_root / f"{args.host_label}_command_records"
    junit_root = evidence_root / f"{args.host_label}_junit"
    for directory in [stdout_root, records_root, junit_root]:
        directory.mkdir()
    external_pycache = evidence_root.parent / "diagnostics" / f"{args.host_label}_external_pycache"
    external_pycache.parent.mkdir(parents=True, exist_ok=True)
    os.environ["HAXS_R32A5_G0_PYCACHE"] = str(external_pycache)
    forbidden = [
        ROOT / "results/stage5c2gR32A5/protocol/AUTHORIZATION.json",
        ROOT / "results/stage5c2gR32A5/protocol/LOCKED.json",
        ROOT / "results/stage5c2gR32A5/protocol/SUPERVISOR_AUTHORIZATION_G1_ONLY.json",
        ROOT / "results/stage5c2gR32A5/state/G1.json",
    ]
    if any(path.exists() or path.is_symlink() for path in forbidden):
        raise RuntimeError("G0 root contains authorization, receipt, lock, or G1 state")
    candidate = load_candidate()
    if not args.protocol.is_file() or args.protocol.is_symlink():
        raise RuntimeError("G0 protocol archive is missing or symlinked")
    protocol = args.protocol.absolute()
    actual_protocol_sha256 = sha256_file(protocol)
    fresh_unzip = verify_protocol(protocol)
    root_before = verify_root(ROOT, candidate)
    environment = verify_environment(ROOT, candidate, install_wheel=True)
    ledger_path = ROOT / candidate["authorization_contract"]["test_ledger"]["path"]
    ledger = strict_json(ledger_path)
    python_sha256 = sha256_file(sys.executable)
    if python_sha256 != candidate["python_executable_sha256"]:
        raise RuntimeError("bound Python executable differs from the candidate")
    full_junit = junit_root / "full_tests.xml"
    targeted_junit = junit_root / "targeted_tests.xml"
    commands = [
        (
            [
                sys.executable, "-I", "-B", "-X",
                f"pycache_prefix={external_pycache}",
                "-m", "compileall", "-q", "src", "scripts", "scripts_patch", "tests",
            ],
            "compileall", 0, None, None,
        ),
        (
            [sys.executable, "-I", "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={full_junit}", *ledger["suites"]["full"]["nodeids"]],
            "full_tests", ledger["counts"]["full"], full_junit, ledger["suites"]["full"]["nodeids"],
        ),
        (
            [sys.executable, "-I", "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={targeted_junit}", *ledger["suites"]["targeted"]["nodeids"]],
            "targeted_tests", ledger["counts"]["targeted"], targeted_junit, ledger["suites"]["targeted"]["nodeids"],
        ),
    ]
    command_records = {}
    for command, stage, count, junit_path, nodeids in commands:
        record_path = records_root / f"{stage}.json"
        run_recorded(
            command, stage, evidence_root, stdout_root / f"{stage}.txt",
            record_path, count, python_sha256, junit_path, nodeids,
        )
        command_records[stage] = {
            "path": record_path.relative_to(evidence_root).as_posix(),
            "sha256": sha256_file(record_path),
        }
    root_after = verify_root(ROOT, candidate)
    if root_after != root_before:
        raise RuntimeError("execution root changed during G0")
    ledger_copy = evidence_root / f"{args.host_label}_NAMED_TEST_LEDGER.json"
    shutil.copy2(ledger_path, ledger_copy)
    primary = {
        "full_junit": {"path": full_junit.relative_to(evidence_root).as_posix(), "sha256": sha256_file(full_junit)},
        "targeted_junit": {"path": targeted_junit.relative_to(evidence_root).as_posix(), "sha256": sha256_file(targeted_junit)},
        "named_test_ledger": {"path": ledger_copy.relative_to(evidence_root).as_posix(), "sha256": sha256_file(ledger_copy)},
        "command_records": command_records,
    }
    full_semantics = verify_junit_semantics(full_junit, ledger["suites"]["full"]["nodeids"])
    targeted_semantics = verify_junit_semantics(targeted_junit, ledger["suites"]["targeted"]["nodeids"])
    semantic_evidence = {
        "full_junit": full_semantics,
        "targeted_junit": targeted_semantics,
        "command_record_sha256": {
            name: strict_json(evidence_root / record["path"])["record_sha256"]
            for name, record in command_records.items()
        },
        "actual_protocol_sha256": actual_protocol_sha256,
    }
    semantic_evidence["semantic_evidence_sha256"] = sha256_payload(semantic_evidence)
    contracts = candidate["authorization_contract"]
    payload = {
        "schema_version": "haxs.stage5c2gR32A5.physical-host-g0.v1",
        "status": "PASS", "host_label": args.host_label,
        "candidate_sha256": candidate["candidate_sha256"],
        "runtime_tree_sha256": candidate["runtime_tree_sha256"],
        "root_manifest_sha256": contracts["root_manifest"]["sha256"],
        "wheel_sha256": candidate["wheel"]["sha256"],
        "environment_sha256": candidate["environment"]["sha256"],
        "dependency_lock_sha256": candidate["dependency_lock"]["sha256"],
        "wheelhouse_manifest_sha256": candidate["wheelhouse_manifest"]["sha256"],
        "protocol_archive_sha256": actual_protocol_sha256,
        "g1_config_sha256": contracts["g1_config"]["sha256"],
        "g1_plan_sha256": contracts["g1_plan"]["sha256"],
        "unit_registry_sha256": contracts["unit_registry"]["sha256"],
        "runner_sha256": contracts["runner"]["sha256"],
        "test_ledger_sha256": contracts["test_ledger"]["sha256"],
        "adversarial_outcomes_sha256": contracts["adversarial_outcomes"]["sha256"],
        "physical_host": physical_identity(), "primary_evidence": primary,
        "semantic_evidence": semantic_evidence, "test_counts": ledger["counts"],
        "scientific_execution_performed": False, "G1_authorized": False,
        "prior_authorization_present": False,
    }
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (evidence_root / f"{args.host_label}_ROOT.json").write_text(json.dumps(root_before, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (evidence_root / f"{args.host_label}_ENVIRONMENT.json").write_text(json.dumps(environment, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (evidence_root / f"{args.host_label}_FRESH_UNZIP.json").write_text(json.dumps(fresh_unzip, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
