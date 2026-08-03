#!/usr/bin/env python
from __future__ import annotations

import json
import os
import secrets
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2gR32A1_authorization import (
    assert_runtime_files,
    assert_root_closure,
    assert_no_unlisted_runtime,
    atomic_write_json,
    load_candidate,
    load_lock,
    reserve_attempt,
    sha256_file,
    sha256_payload,
    terminalize_attempt,
)


def main() -> None:
    if not sys.flags.isolated or sys.flags.no_user_site != 1:
        raise RuntimeError("official R3.2A.1 G1 requires Python isolated mode (-I)")
    if len(sys.argv) != 1:
        raise SystemExit("official R3.2A.1 G1 accepts no overrides")
    candidate = load_candidate()
    assert_runtime_files(candidate)
    assert_root_closure(candidate)
    assert_no_unlisted_runtime(candidate)
    lock = load_lock(candidate)
    launcher_sha = sha256_file(Path(__file__))
    if launcher_sha != candidate["authorization_contract"]["launcher"]["sha256"]:
        raise RuntimeError("official launcher differs from candidate identity")
    wheel = ROOT / candidate["wheel"]["path"]
    if (
        not wheel.is_file()
        or wheel.is_symlink()
        or sha256_file(wheel) != candidate["wheel"]["sha256"]
    ):
        raise RuntimeError("candidate-bound wheel identity failed")

    running = reserve_attempt(candidate, lock)
    output = ROOT / running["artifact_path"]
    environment = {
        key: value
        for key, value in os.environ.items()
        if key
        not in {
            "PYTHONPATH",
            "PYTHONHOME",
            "PYTHONSTARTUP",
            "PYTHONINSPECT",
            "PYTHONUSERBASE",
            "LD_PRELOAD",
            "DYLD_INSERT_LIBRARIES",
            "DYLD_LIBRARY_PATH",
        }
    }
    environment.update(
        {
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "VECLIB_MAXIMUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
        }
    )
    try:
        with tempfile.TemporaryDirectory(
            prefix="haxs-stage5c2gR32A1-official-G1-"
        ) as directory:
            temporary = Path(directory)
            installed = temporary / "installed"
            installed.mkdir()
            completed = subprocess.run(
                [
                    sys.executable,
                    "-I",
                    "-m",
                    "pip",
                    "install",
                    "--no-deps",
                    "--no-compile",
                    "--target",
                    str(installed),
                    str(wheel),
                ],
                cwd=temporary,
                env=environment,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            if completed.returncode:
                output.mkdir(parents=True, exist_ok=False)
                (output / "WHEEL_INSTALL_TRANSCRIPT.txt").write_text(
                    completed.stdout + f"\nEXIT_STATUS={completed.returncode}\n",
                    encoding="utf-8",
                )
                raise RuntimeError("candidate-bound wheel installation failed")
            wheel_install_transcript = (
                completed.stdout + f"\nEXIT_STATUS={completed.returncode}\n"
            )
            attestation = {
                "schema_version": "haxs.stage5c2gR32A1.G1-launch.v1",
                "candidate_sha256": candidate["candidate_sha256"],
                "lock_sha256": lock["lock_sha256"],
                "wheel_sha256": candidate["wheel"]["sha256"],
                "installed_target": str(installed.resolve()),
                "execution_root": str(ROOT.resolve()),
                "output_path": str(output.resolve()),
                "nonce": secrets.token_hex(32),
                "launcher_sha256": launcher_sha,
            }
            attestation_path = temporary / "LAUNCH_ATTESTATION.json"
            atomic_write_json(attestation_path, attestation)
            environment["HAXS_R32A1_LAUNCH_ATTESTATION"] = str(attestation_path)
            completed = subprocess.run(
                [
                    sys.executable,
                    "-I",
                    "scripts/run_stage5c2gR32A1_G1.py",
                ],
                cwd=ROOT,
                env=environment,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            output.mkdir(parents=True, exist_ok=True)
            (output / "WHEEL_INSTALL_TRANSCRIPT.txt").write_text(
                wheel_install_transcript,
                encoding="utf-8",
            )
            (output / "G1_EXECUTION_TRANSCRIPT.txt").write_text(
                completed.stdout + f"\nEXIT_STATUS={completed.returncode}\n",
                encoding="utf-8",
            )
            if completed.returncode:
                raise RuntimeError("official deterministic G1 runner failed")
            official_manifest_path = output / "OFFICIAL_G1_MANIFEST.json"
            official_manifest = json.loads(
                official_manifest_path.read_text(encoding="utf-8")
            )
            official_manifest["files"] = {
                path.relative_to(output).as_posix(): sha256_file(path)
                for path in sorted(output.rglob("*"))
                if path.is_file() and path != official_manifest_path
            }
            official_manifest.pop("manifest_sha256", None)
            official_manifest["manifest_sha256"] = sha256_payload(
                official_manifest
            )
            atomic_write_json(official_manifest_path, official_manifest)
        verification = output / "OFFICIAL_G1_VERIFICATION.json"
        manifest = output / "OFFICIAL_G1_MANIFEST.json"
        if (
            not verification.is_file()
            or json.loads(verification.read_text(encoding="utf-8")).get("status")
            != "PASS"
            or not manifest.is_file()
        ):
            raise RuntimeError("official deterministic G1 evidence is incomplete")
        terminal = terminalize_attempt(
            running,
            "PASSED",
            {
                "verification_sha256": sha256_file(verification),
                "manifest_sha256": sha256_file(manifest),
                "error": "",
            },
        )
        print(
            json.dumps(
                {
                    "gate": "G1",
                    "status": "PASSED",
                    "attempt_id": running["attempt_id"],
                    "candidate_sha256": candidate["candidate_sha256"],
                    "state_sha256": terminal["state_sha256"],
                    "next": "STOP_AND_RETURN_FOR_SUPERVISORY_REVIEW",
                },
                indent=2,
                sort_keys=True,
            )
        )
    except Exception as error:
        terminalize_attempt(running, "FAILED", {"error": repr(error)})
        raise


if __name__ == "__main__":
    main()
