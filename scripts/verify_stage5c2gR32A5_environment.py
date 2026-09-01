#!/usr/bin/env python
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from stage5c2gR32A2_common import sha256_payload, strict_json, verify_record
from stage5c2gR32A5_common import load_candidate
from verify_stage5c2gR32A2_environment import (
    DANGEROUS_ENVIRONMENT,
    current_environment,
    installed_wheel_tree_identity,
)


def verify_environment(root: Path, candidate: dict | None = None, install_wheel: bool = True) -> dict:
    if not sys.flags.isolated or sys.flags.no_user_site != 1:
        raise RuntimeError("A5 environment verification requires -I")
    dangerous = sorted(name for name in DANGEROUS_ENVIRONMENT if os.environ.get(name))
    if dangerous:
        raise RuntimeError(f"dangerous import environment present: {dangerous}")
    candidate = candidate or load_candidate(root)
    declared = strict_json(verify_record(root, candidate["environment"], "environment"))
    canonical = {key: value for key, value in declared.items() if key != "environment_sha256"}
    if (
        declared.get("schema_version") != "haxs.stage5c2gR32A5.environment.v1"
        or declared.get("environment_sha256") != sha256_payload(canonical)
    ):
        raise RuntimeError("A5 environment self-identity failed")
    for field, value in current_environment().items():
        if declared.get(field) != value:
            raise RuntimeError(f"exact environment mismatch: {field}")
    if any(os.environ.get(key) != value for key, value in declared["thread_environment"].items()):
        raise RuntimeError("numerical thread environment mismatch")
    wheel = verify_record(root, candidate["wheel"], "wheel")
    installed_sha = "NOT_REQUESTED"
    if install_wheel:
        with tempfile.TemporaryDirectory(prefix="haxs-stage5c2gR32A5-install-") as directory:
            target = Path(directory) / "site"
            clean = {key: value for key, value in os.environ.items() if key not in DANGEROUS_ENVIRONMENT}
            completed = subprocess.run(
                [sys.executable, "-I", "-m", "pip", "install", "--no-index", "--no-deps", "--no-compile", "--target", str(target), str(wheel)],
                cwd=directory, env=clean, text=True,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            )
            if completed.returncode:
                raise RuntimeError("A5 candidate wheel installation failed")
            installed_sha = installed_wheel_tree_identity(target, wheel)["payload_tree_sha256"]
            if installed_sha != declared["installed_wheel_tree_sha256"]:
                raise RuntimeError("installed A5 wheel tree identity failed")
    return {
        "stage": "stage5c2gR32A5_environment", "status": "PASS",
        "candidate_sha256": candidate["candidate_sha256"],
        "environment_sha256": declared["environment_sha256"],
        "installed_wheel_tree_sha256": installed_sha,
        "isolated": True, "setup_complete_before_attempt_reservation": True,
    }
