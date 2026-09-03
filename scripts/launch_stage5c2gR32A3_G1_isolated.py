#!/usr/bin/env python
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2gR32A3_common import (
    AUTHORIZATION_PATH, SETUP_STATE_PATH, exclusive_write_json, load_candidate,
    reserve_attempt, sha256_file, sha256_payload, strict_json, terminalize_attempt,
)
from verify_stage5c2gR32A3_environment import verify_environment
from verify_stage5c2gR32A3_root import verify_root


def load_authorization(candidate: dict) -> dict:
    authorization = strict_json(ROOT / AUTHORIZATION_PATH.relative_to(ROOT))
    canonical = {key: value for key, value in authorization.items() if key != "authorization_sha256"}
    if (
        authorization.get("schema_version") != "haxs.stage5c2gR32A3.atomic-authorization.v1"
        or authorization.get("status") != "LOCKED_G1_ONLY"
        or authorization.get("candidate_sha256") != candidate["candidate_sha256"]
        or authorization.get("authorization_sha256") != sha256_payload(canonical)
        or authorization.get("official_attempt_limit") != 1
    ):
        raise RuntimeError("atomic R3.2A.3 authorization failed")
    return authorization


def preflight_and_reserve(candidate: dict, authorization: dict, root: Path = ROOT) -> tuple[dict, dict]:
    root_result = verify_root(root, candidate)
    environment_result = verify_environment(root, candidate, install_wheel=True)
    launcher = root / "scripts/launch_stage5c2gR32A3_G1_isolated.py"
    if sha256_file(launcher) != candidate["authorization_contract"]["launcher"]["sha256"]:
        raise RuntimeError("candidate-bound launcher identity failed")
    setup = {
        "schema_version": "haxs.stage5c2gR32A3.setup-preflight.v1", "status": "PASS",
        "candidate_sha256": candidate["candidate_sha256"], "root": root_result,
        "environment": environment_result, "scientific_attempt_reserved": False,
    }
    setup["setup_sha256"] = sha256_payload(setup)
    exclusive_write_json(root / SETUP_STATE_PATH.relative_to(ROOT), setup)
    return setup, reserve_attempt(candidate, authorization, root)


def main() -> None:
    if not sys.flags.isolated or len(sys.argv) != 1:
        raise RuntimeError("official R3.2A.3 G1 requires isolated no-override execution")
    candidate = load_candidate()
    authorization = load_authorization(candidate)
    _, running = preflight_and_reserve(candidate, authorization)
    output = ROOT / running["artifact_path"]
    clean = {key: value for key, value in os.environ.items() if not key.startswith("PYTHON") and not key.startswith("DYLD_") and key != "LD_PRELOAD"}
    clean.update({"PYTHONDONTWRITEBYTECODE": "1", "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "VECLIB_MAXIMUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1"})
    try:
        completed = subprocess.run(
            [sys.executable, "-I", "-B", "scripts/run_stage5c2gR32A3_G1.py"],
            cwd=ROOT, env=clean, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        output.mkdir(parents=True, exist_ok=True)
        transcript = output / "G1_EXECUTION_TRANSCRIPT.txt"
        transcript.write_text(completed.stdout + f"\nEXIT_STATUS={completed.returncode}\n", encoding="utf-8")
        if completed.returncode:
            raise RuntimeError("official deterministic G1 runner failed")
        terminal = terminalize_attempt(running, "PASSED", {"transcript_sha256": sha256_file(transcript), "error": ""})
        print(json.dumps({"gate": "G1", "status": "PASSED", "attempt_id": running["attempt_id"], "state_sha256": terminal["state_sha256"], "next": "STOP_AND_RETURN_FOR_SUPERVISORY_REVIEW"}, indent=2, sort_keys=True))
    except Exception as error:
        terminalize_attempt(running, "FAILED", {"error": repr(error)})
        raise


if __name__ == "__main__":
    main()
