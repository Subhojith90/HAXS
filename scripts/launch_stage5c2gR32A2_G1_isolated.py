#!/usr/bin/env python
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2gR32A2_common import (
    AUTHORIZATION_PATH, SETUP_STATE_PATH, exclusive_write_json, load_candidate,
    reserve_attempt, sha256_file, sha256_payload, strict_json, terminalize_attempt,
)
from verify_stage5c2gR32A2_environment import verify_environment
from verify_stage5c2gR32A2_root import verify_root


def load_authorization(candidate: dict) -> dict:
    authorization = strict_json(ROOT / AUTHORIZATION_PATH.relative_to(ROOT))
    canonical = {key: value for key, value in authorization.items() if key != "authorization_sha256"}
    if (
        authorization.get("schema_version") != "haxs.stage5c2gR32A2.atomic-authorization.v1"
        or authorization.get("status") != "LOCKED_G1_ONLY"
        or authorization.get("candidate_sha256") != candidate["candidate_sha256"]
        or authorization.get("authorization_sha256") != sha256_payload(canonical)
        or authorization.get("official_attempt_limit") != 1
        or authorization.get("setup_preflight_required_before_attempt") is not True
    ):
        raise RuntimeError("atomic R3.2A.2 authorization failed")
    return authorization


def preflight_and_reserve(
    candidate: dict,
    authorization: dict,
    root: Path = ROOT,
    root_verifier=verify_root,
    environment_verifier=verify_environment,
) -> tuple[dict, dict]:
    """Complete setup atomically before touching the one-shot scientific state."""
    root_result = root_verifier(root, candidate)
    environment_result = environment_verifier(root, candidate, install_wheel=True)
    launcher = root / "scripts/launch_stage5c2gR32A2_G1_isolated.py"
    launcher_sha = sha256_file(launcher)
    if launcher_sha != candidate["authorization_contract"]["launcher"]["sha256"]:
        raise RuntimeError("candidate-bound launcher identity failed")
    setup = {
        "schema_version": "haxs.stage5c2gR32A2.setup-preflight.v1",
        "status": "PASS",
        "candidate_sha256": candidate["candidate_sha256"],
        "root": root_result,
        "environment": environment_result,
        "scientific_attempt_reserved": False,
    }
    setup["setup_sha256"] = sha256_payload(setup)
    setup_path = root / SETUP_STATE_PATH.relative_to(ROOT)
    if setup_path.exists() or setup_path.is_symlink():
        raise RuntimeError("setup preflight record already exists")
    exclusive_write_json(setup_path, setup)
    running = reserve_attempt(candidate, authorization, root)
    return setup, running


def main() -> None:
    if not sys.flags.isolated or sys.flags.no_user_site != 1:
        raise RuntimeError("official R3.2A.2 G1 requires isolated Python (-I)")
    if len(sys.argv) != 1:
        raise SystemExit("official R3.2A.2 G1 accepts no overrides")
    candidate = load_candidate()
    authorization = load_authorization(candidate)

    # SETUP PREFLIGHT: every operation here must complete before the exclusive
    # scientific-attempt state is created. A failure therefore consumes no attempt.
    # The one-shot state is reserved inside this call only after root, import,
    # native-library, environment and immutable-wheel checks have all passed.
    _, running = preflight_and_reserve(candidate, authorization)
    output = ROOT / running["artifact_path"]
    clean_environment = {
        key: value for key, value in os.environ.items()
        if key not in {
            "PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP", "PYTHONINSPECT", "PYTHONUSERBASE",
            "LD_PRELOAD", "DYLD_INSERT_LIBRARIES", "DYLD_LIBRARY_PATH",
        }
    }
    clean_environment.update({
        "PYTHONDONTWRITEBYTECODE": "1", "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
        "VECLIB_MAXIMUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1",
    })
    try:
        completed = subprocess.run(
            [sys.executable, "-I", "scripts/run_stage5c2gR32A2_G1.py"],
            cwd=ROOT, env=clean_environment, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        output.mkdir(parents=True, exist_ok=True)
        transcript = output / "G1_EXECUTION_TRANSCRIPT.txt"
        transcript.write_text(completed.stdout + f"\nEXIT_STATUS={completed.returncode}\n", encoding="utf-8")
        if completed.returncode:
            raise RuntimeError("official deterministic G1 runner failed")
        terminal = terminalize_attempt(running, "PASSED", {"transcript_sha256": sha256_file(transcript), "error": ""})
        print(json.dumps({
            "gate": "G1", "status": "PASSED", "attempt_id": running["attempt_id"],
            "candidate_sha256": candidate["candidate_sha256"],
            "state_sha256": terminal["state_sha256"],
            "next": "STOP_AND_RETURN_FOR_SUPERVISORY_REVIEW",
        }, indent=2, sort_keys=True))
    except Exception as error:
        terminalize_attempt(running, "FAILED", {"error": repr(error)})
        raise


if __name__ == "__main__":
    main()
