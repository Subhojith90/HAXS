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
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2gR32A2_common import (
    AUTHORIZATION_PATH, LOCK_PATH, RECEIPT_PATH, STATE_PATH,
    load_candidate, sha256_file, strict_json,
)
from verify_stage5c2gR32A2_environment import verify_environment
from verify_stage5c2gR32A2_fresh_unzip import verify_protocol
from verify_stage5c2gR32A2_root import verify_root


def physical_identity() -> dict:
    values: list[str]
    if platform.system() == "Darwin":
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
    else:
        machine_id = Path("/etc/machine-id")
        if not machine_id.is_file():
            raise RuntimeError("physical host identity unavailable")
        values = [machine_id.read_text(encoding="utf-8").strip(), platform.node()]
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
        "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPYCACHEPREFIX": os.environ["HAXS_R32A2_G0_PYCACHE"],
        "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
        "VECLIB_MAXIMUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1",
    })
    return environment


def run(command: list[str], transcript: Path) -> None:
    completed = subprocess.run(
        command, cwd=ROOT, env=clean_environment(), text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    transcript.write_text(
        "$ " + " ".join(command) + "\n" + completed.stdout + f"\nEXIT_STATUS={completed.returncode}\n",
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
    if not sys.flags.isolated or sys.version_info[:3] != (3, 12, 7):
        raise RuntimeError("G0 requires isolated exact CPython 3.12.7")
    evidence_root = args.out.parent.resolve()
    if args.out.exists() or args.out.is_symlink() or evidence_root.exists():
        raise RuntimeError("G0 evidence root must not already exist")
    evidence_root.mkdir(parents=True)
    transcripts = evidence_root / f"{args.host_label}_transcripts"
    junit = evidence_root / f"{args.host_label}_junit"
    transcripts.mkdir()
    junit.mkdir()
    external_pycache = evidence_root.parent / "diagnostics" / f"{args.host_label}_external_pycache"
    external_pycache.parent.mkdir(parents=True, exist_ok=True)
    os.environ["HAXS_R32A2_G0_PYCACHE"] = str(external_pycache)

    forbidden = [ROOT / path.relative_to(ROOT) for path in [AUTHORIZATION_PATH, LOCK_PATH, RECEIPT_PATH, STATE_PATH]]
    if any(path.exists() or path.is_symlink() for path in forbidden):
        raise RuntimeError("G0 root contains authorization, receipt, lock, or G1 state")
    candidate = load_candidate()
    protocol = args.protocol.resolve()
    fresh = verify_protocol(protocol)
    root_before = verify_root(ROOT, candidate)
    environment = verify_environment(ROOT, candidate, install_wheel=True)
    ledger_path = ROOT / candidate["authorization_contract"]["test_ledger"]["path"]
    ledger = strict_json(ledger_path)
    commands = [
        ([sys.executable, "-m", "compileall", "-q", "src", "scripts", "scripts_patch", "tests"], "00_compileall.txt"),
        ([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={junit / 'full_tests.xml'}", *ledger["suites"]["full"]["nodeids"]], "01_full_tests.txt"),
        ([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={junit / 'targeted_tests.xml'}", *ledger["suites"]["targeted"]["nodeids"]], "02_targeted_tests.txt"),
    ]
    for command, name in commands:
        run(command, transcripts / name)
    root_after = verify_root(ROOT, candidate)
    if root_after != root_before:
        raise RuntimeError("execution root changed during G0")
    (transcripts / "03_root_before.json").write_text(json.dumps(root_before, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (transcripts / "04_environment.json").write_text(json.dumps(environment, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (transcripts / "05_fresh_unzip.json").write_text(json.dumps(fresh, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    ledger_copy = evidence_root / f"{args.host_label}_NAMED_TEST_LEDGER.json"
    shutil.copy2(ledger_path, ledger_copy)
    primary = {
        "full_junit": {"path": (junit / "full_tests.xml").relative_to(evidence_root).as_posix(), "sha256": sha256_file(junit / "full_tests.xml")},
        "targeted_junit": {"path": (junit / "targeted_tests.xml").relative_to(evidence_root).as_posix(), "sha256": sha256_file(junit / "targeted_tests.xml")},
        "named_test_ledger": {"path": ledger_copy.relative_to(evidence_root).as_posix(), "sha256": sha256_file(ledger_copy)},
        "transcripts": [
            {"path": path.relative_to(evidence_root).as_posix(), "sha256": sha256_file(path)}
            for path in sorted(transcripts.iterdir()) if path.is_file()
        ],
    }
    contracts = candidate["authorization_contract"]
    payload = {
        "schema_version": "haxs.stage5c2gR32A2.physical-host-g0.v1", "status": "PASS",
        "host_label": args.host_label, "candidate_sha256": candidate["candidate_sha256"],
        "runtime_tree_sha256": candidate["runtime_tree_sha256"],
        "root_manifest_sha256": contracts["root_manifest"]["sha256"],
        "wheel_sha256": candidate["wheel"]["sha256"], "environment_sha256": candidate["environment"]["sha256"],
        "dependency_lock_sha256": candidate["dependency_lock"]["sha256"],
        "wheelhouse_manifest_sha256": candidate["wheelhouse_manifest"]["sha256"],
        "protocol_archive_sha256": sha256_file(protocol),
        "g1_config_sha256": contracts["g1_config"]["sha256"], "g1_plan_sha256": contracts["g1_plan"]["sha256"],
        "unit_registry_sha256": contracts["unit_registry"]["sha256"], "runner_sha256": contracts["runner"]["sha256"],
        "test_ledger_sha256": contracts["test_ledger"]["sha256"],
        "adversarial_outcomes_sha256": contracts["adversarial_outcomes"]["sha256"],
        "physical_host": physical_identity(), "primary_evidence": primary,
        "test_counts": ledger["counts"], "scientific_execution_performed": False,
        "G1_authorized": False, "prior_authorization_present": False,
    }
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
