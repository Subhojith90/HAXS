#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from stage5c2gR32A5_common import (
    AUTHORIZATION_NAME,
    SETUP_NAME,
    candidate_control_root,
    exclusive_write_json,
    load_candidate,
    reserve_attempt,
    sha256_file,
    sha256_payload,
    strict_json,
    terminalize_attempt,
    verify_control_root,
)
from stage5c2gR32A2_common import safe_relative


def load_authorization(control_root: Path, candidate: dict, immutable_root: Path = ROOT) -> dict:
    verify_control_root(control_root, candidate, "AUTHORIZED", immutable_root)
    namespace = candidate_control_root(control_root, candidate, immutable_root)
    return strict_json(namespace / AUTHORIZATION_NAME)


def verify_execution_contracts(immutable_root: Path, candidate: dict) -> dict:
    contracts = candidate.get("authorization_contract")
    required = {"launcher", "runner", "g1_config", "g1_plan", "unit_registry"}
    if not isinstance(contracts, dict) or not required.issubset(contracts):
        raise RuntimeError("A5 candidate lacks mandatory execution contracts")
    verified = {}
    for name in sorted(required):
        record = contracts[name]
        if set(record) != {"path", "sha256"}:
            raise RuntimeError(f"A5 {name} contract schema failed")
        path = immutable_root / safe_relative(record["path"])
        if not path.is_file() or path.is_symlink() or sha256_file(path) != record["sha256"]:
            raise RuntimeError(f"A5 {name} contract identity failed")
        verified[name] = record["sha256"]
    return verified


def preflight_and_reserve(
    candidate: dict,
    authorization: dict,
    control_root: Path,
    immutable_root: Path = ROOT,
    root_verifier=None,
    environment_verifier=None,
) -> tuple[dict, dict]:
    if root_verifier is None:
        from verify_stage5c2gR32A5_root import verify_root
        root_verifier = verify_root
    if environment_verifier is None:
        from verify_stage5c2gR32A5_environment import verify_environment
        environment_verifier = verify_environment
    root_result = root_verifier(immutable_root, candidate)
    environment_result = environment_verifier(immutable_root, candidate, install_wheel=True)
    execution_contracts = verify_execution_contracts(immutable_root, candidate)
    namespace = candidate_control_root(control_root, candidate, immutable_root)
    setup = {
        "schema_version": "haxs.stage5c2gR32A5.setup-preflight.v1",
        "status": "PASS",
        "candidate_sha256": candidate["candidate_sha256"],
        "immutable_root": root_result,
        "environment": environment_result,
        "execution_contracts": execution_contracts,
        "scientific_attempt_reserved": False,
    }
    setup["setup_sha256"] = sha256_payload(setup)
    exclusive_write_json(namespace / SETUP_NAME, setup)
    verify_control_root(control_root, candidate, "SETUP", immutable_root)
    running = reserve_attempt(control_root, candidate, authorization, immutable_root)
    verify_control_root(control_root, candidate, "RUNNING", immutable_root)
    return setup, running


def execute_once(
    candidate: dict,
    authorization: dict,
    control_root: Path,
    runner,
    immutable_root: Path = ROOT,
    root_verifier=None,
    environment_verifier=None,
) -> dict:
    _, running = preflight_and_reserve(
        candidate, authorization, control_root, immutable_root,
        root_verifier=root_verifier, environment_verifier=environment_verifier,
    )
    transcript = ""
    scientific_output = None
    try:
        result = runner()
        if not isinstance(result, tuple) or len(result) not in {2, 3}:
            raise RuntimeError("official runner returned an invalid execution contract")
        status, transcript = result[:2]
        scientific_output = result[2] if len(result) == 3 else None
        if status != 0:
            raise RuntimeError(f"official runner failed with exit status {status}")
        terminal = terminalize_attempt(
            control_root, candidate, running, "PASSED",
            transcript + f"\nEXIT_STATUS={status}\n",
            scientific_output=scientific_output, immutable_root=immutable_root,
        )
    except Exception as error:
        failure_transcript = transcript
        if failure_transcript and not failure_transcript.endswith("\n"):
            failure_transcript += "\n"
        failure_transcript += f"{error!r}\nEXIT_STATUS=1\n"
        terminalize_attempt(
            control_root, candidate, running, "FAILED",
            failure_transcript, error=repr(error),
            scientific_output=(
                scientific_output
                if scientific_output is not None and scientific_output.is_dir()
                else None
            ),
            immutable_root=immutable_root,
        )
        raise
    verify_control_root(control_root, candidate, "TERMINAL", immutable_root)
    return terminal


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--control-root", type=Path, required=True)
    args = parser.parse_args()
    if not sys.flags.isolated:
        raise RuntimeError("official A5 launcher requires isolated execution")
    candidate = load_candidate()
    authorization = load_authorization(args.control_root, candidate)
    clean = {
        key: value for key, value in os.environ.items()
        if not key.startswith("PYTHON") and not key.startswith("DYLD_") and key != "LD_PRELOAD"
    }
    clean.update({
        "PYTHONDONTWRITEBYTECODE": "1", "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
        "VECLIB_MAXIMUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1",
    })

    wheel = ROOT / safe_relative(candidate["wheel"]["path"])
    with tempfile.TemporaryDirectory(prefix="haxs-stage5c2gR32A5-official-runner-") as directory:
        temporary = Path(directory)
        installed = temporary / "installed-wheel"
        install = subprocess.run(
            [
                sys.executable, "-I", "-m", "pip", "install", "--no-index",
                "--no-deps", "--no-compile", "--target", str(installed), str(wheel),
            ],
            cwd=temporary, env=clean, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        if install.returncode:
            raise RuntimeError("official A5 runner wheel installation failed before reservation")
        output = temporary / "scientific-output"
        attestation = temporary / "LAUNCH_ATTESTATION.json"
        attestation_payload = {
            "schema_version": "haxs.stage5c2gR32A5.G1-launch.v1",
            "candidate_sha256": candidate["candidate_sha256"],
            "receipt_id": authorization["receipt_id"],
            "wheel_sha256": candidate["wheel"]["sha256"],
            "runner_sha256": candidate["authorization_contract"]["runner"]["sha256"],
            "g1_config_sha256": candidate["authorization_contract"]["g1_config"]["sha256"],
            "installed_target": str(installed),
            "output_path": str(output),
        }
        attestation_payload["attestation_sha256"] = sha256_payload(attestation_payload)
        attestation.write_text(
            json.dumps(attestation_payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        clean["HAXS_R32A5_LAUNCH_ATTESTATION"] = str(attestation)
        clean["HAXS_R32A1_INSTALLED_TARGET"] = str(installed)

        def runner() -> tuple[int, str, Path]:
            completed = subprocess.run(
                [sys.executable, "-I", "-B", "scripts/run_stage5c2gR32A5_G1.py"],
                cwd=ROOT, env=clean, text=True,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            )
            return completed.returncode, completed.stdout, output

        terminal = execute_once(candidate, authorization, args.control_root, runner)
    print(json.dumps({
        "gate": "G1", "status": terminal["status"],
        "attempt_id": terminal["attempt_id"],
        "next": "STOP_AND_RETURN_FOR_SUPERVISORY_REVIEW",
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
