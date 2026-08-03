#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2gR32A1_authorization import (
    assert_no_unlisted_runtime,
    assert_runtime_files,
    load_candidate,
    sha256_file,
)
from verify_stage5c2gR32A1_fresh_unzip import verify_protocol
from verify_stage5c2gR32A1_test_ledger import verify_ledger


def verify_current_execution_root() -> dict:
    ledger_path = ROOT / "BUNDLE_CONTENTS_SHA256.txt"
    if not ledger_path.is_file() or ledger_path.is_symlink():
        raise RuntimeError("current execution root has no safe bundle ledger")
    expected: dict[str, str] = {}
    for line in ledger_path.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        if relative in expected:
            raise RuntimeError("current execution-root ledger has a duplicate path")
        expected[relative] = digest
    actual = {
        path.relative_to(ROOT).as_posix(): sha256_file(path)
        for path in ROOT.rglob("*")
        if path.is_file()
        and path.name != "BUNDLE_CONTENTS_SHA256.txt"
        and ".git" not in path.parts
    }
    if actual != expected:
        raise RuntimeError(
            "current execution root differs from the exact protocol ledger"
        )
    return {"status": "PASS", "files": len(actual)}


def physical_identity() -> dict:
    values: list[str] = []
    if platform.system() == "Darwin":
        result = subprocess.run(
            ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
            text=True,
            capture_output=True,
            check=True,
        ).stdout
        for key in ["IOPlatformUUID", "IOPlatformSerialNumber"]:
            match = re.search(rf'"{key}"\s*=\s*"([^"]+)"', result)
            if not match:
                raise RuntimeError(f"physical host field unavailable: {key}")
            values.append(match.group(1))
    else:
        machine_id = Path("/etc/machine-id")
        if not machine_id.is_file():
            raise RuntimeError("physical host identity unavailable")
        values = [machine_id.read_text(encoding="utf-8").strip(), platform.node()]
    return {
        "system": platform.system(),
        "machine": platform.machine(),
        "platform_identity_sha256": hashlib.sha256(values[0].encode()).hexdigest(),
        "serial_or_node_sha256": hashlib.sha256(values[1].encode()).hexdigest(),
    }


def clean_environment() -> dict[str, str]:
    excluded = {
        "PYTHONPATH",
        "PYTHONHOME",
        "PYTHONSTARTUP",
        "PYTHONINSPECT",
        "PYTHONUSERBASE",
        "LD_PRELOAD",
        "DYLD_INSERT_LIBRARIES",
        "DYLD_LIBRARY_PATH",
        "HAXS_CUSTODY_ROOT",
    }
    environment = {
        key: value for key, value in os.environ.items() if key not in excluded
    }
    environment.update(
        {
            "PYTHONPYCACHEPREFIX": os.environ["HAXS_R32A1_G0_PYCACHE"],
            "PYTHONDONTWRITEBYTECODE": "1",
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "VECLIB_MAXIMUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
        }
    )
    return environment


def run(command: list[str], transcript: Path) -> None:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=clean_environment(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    transcript.write_text(
        "$ " + " ".join(command) + "\n" + completed.stdout
        + f"\nEXIT_STATUS={completed.returncode}\n",
        encoding="utf-8",
    )
    if completed.returncode:
        raise RuntimeError(f"G0 command failed: {' '.join(command)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host-label", choices=["HOST_A", "HOST_B"], required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if sys.version_info[:3] != (3, 12, 7):
        raise RuntimeError("G0 requires exact CPython 3.12.7")
    if args.out.exists() or args.out.is_symlink():
        raise RuntimeError("refusing to overwrite G0 host evidence")
    transcript_dir = args.out.parent / f"{args.host_label}_transcripts"
    junit_dir = args.out.parent / f"{args.host_label}_junit"
    if transcript_dir.exists() or junit_dir.exists():
        raise RuntimeError("refusing to overwrite G0 transcript or JUnit evidence")
    transcript_dir.mkdir(parents=True)
    junit_dir.mkdir(parents=True)
    os.environ["HAXS_R32A1_G0_PYCACHE"] = str(
        args.out.parent / f"{args.host_label}_pycache"
    )

    protocol = args.protocol.resolve()
    fresh = verify_protocol(protocol, strict_root=True)
    current_root = verify_current_execution_root()
    candidate = load_candidate()
    assert_runtime_files(candidate)
    assert_no_unlisted_runtime(candidate)
    if fresh["candidate_sha256"] != candidate["candidate_sha256"]:
        raise RuntimeError("protocol and execution-root candidates differ")
    ledger_path = ROOT / candidate["authorization_contract"]["test_ledger"]["path"]
    ledger_result = verify_ledger(ledger_path)
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))

    commands = [
        (
            [
                sys.executable,
                "-m",
                "compileall",
                "-q",
                "src",
                "scripts",
                "scripts_patch",
                "tests",
            ],
            "00_compileall.txt",
        ),
        (
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                f"--junitxml={junit_dir / 'full_tests.xml'}",
                *ledger["suites"]["full"]["nodeids"],
            ],
            "01_full_tests.txt",
        ),
        (
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                f"--junitxml={junit_dir / 'targeted_tests.xml'}",
                *ledger["suites"]["targeted"]["nodeids"],
            ],
            "02_targeted_tests.txt",
        ),
        (
            [
                sys.executable,
                "-I",
                "scripts/verify_stage5c2gR32A1_immutable_install.py",
            ],
            "03_immutable_install.txt",
        ),
    ]
    for command, name in commands:
        run(command, transcript_dir / name)
    (transcript_dir / "04_fresh_unzip.json").write_text(
        json.dumps(fresh, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (transcript_dir / "05_named_test_ledger.json").write_text(
        json.dumps(ledger_result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (transcript_dir / "06_current_execution_root.json").write_text(
        json.dumps(current_root, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    contracts = candidate["authorization_contract"]
    transcript_hashes = {
        path.name: sha256_file(path)
        for path in sorted(transcript_dir.iterdir())
        if path.is_file()
    }
    junit_hashes = {
        path.name: sha256_file(path)
        for path in sorted(junit_dir.iterdir())
        if path.is_file()
    }
    payload = {
        "schema_version": "haxs.stage5c2gR32A1.physical-host-g0.v1",
        "status": "PASS",
        "host_label": args.host_label,
        "candidate_sha256": candidate["candidate_sha256"],
        "runtime_tree_sha256": candidate["runtime_tree_sha256"],
        "wheel_sha256": candidate["wheel"]["sha256"],
        "environment_sha256": candidate["environment"]["sha256"],
        "protocol_archive_sha256": sha256_file(protocol),
        "g1_config_sha256": contracts["g1_config"]["sha256"],
        "g1_plan_sha256": contracts["g1_plan"]["sha256"],
        "unit_registry_sha256": contracts["unit_registry"]["sha256"],
        "runner_sha256": contracts["runner"]["sha256"],
        "test_ledger_sha256": contracts["test_ledger"]["sha256"],
        "root_manifest_sha256": contracts["root_manifest"]["sha256"],
        "python_version": platform.python_version(),
        "physical_host": physical_identity(),
        "transcript_sha256": transcript_hashes,
        "junit_sha256": junit_hashes,
        "external_root_reconstruction_required": False,
        "scientific_execution_performed": False,
        "G1_authorized": False,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
