#!/usr/bin/env python
from __future__ import annotations

import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2gR3_common import assert_protocol_locked, require_isolated_interpreter, sha256_file
from stage5c2gR3_state import atomic_write_json


def main() -> None:
    require_isolated_interpreter(ROOT)
    if len(sys.argv) != 1:
        raise SystemExit("isolated G1 launcher accepts no source, configuration, evidence, or output overrides")
    lock = assert_protocol_locked(ROOT)
    wheel = ROOT / "output/stage5c2gR3/haxs-0.8.1-py3-none-any.whl"
    expected_wheel = lock["candidate_payload"]["installed_wheel"]["wheel_sha256"]
    if not wheel.is_file() or wheel.is_symlink() or sha256_file(wheel) != expected_wheel:
        raise RuntimeError("official G1 launcher wheel differs from the candidate-bound installed wheel")
    dangerous = set(lock["candidate_payload"]["environment"]["spec"].get("dangerous_environment_variables", []))
    dangerous.update({"PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP", "PYTHONINSPECT", "PYTHONUSERBASE", "LD_PRELOAD", "DYLD_INSERT_LIBRARIES", "DYLD_LIBRARY_PATH"})
    clean_environment = {key: value for key, value in os.environ.items() if key not in dangerous}
    with tempfile.TemporaryDirectory(prefix="stage5c2gR3_1_official_G1_") as name:
        root = Path(name); installed = root / "installed"; installed.mkdir()
        completed = subprocess.run([sys.executable, "-I", "-m", "pip", "install", "--no-deps", "--target", str(installed), str(wheel)], env=clean_environment, text=True, capture_output=True)
        if completed.returncode != 0:
            raise RuntimeError("candidate-bound wheel installation failed:\n" + completed.stdout + completed.stderr)
        attestation_path = root / "LAUNCH_ATTESTATION.json"
        launch = {"schema_version": "stage5c2gR3.1.G1-launch.v1", "candidate_sha256": lock["candidate_sha256"], "wheel_sha256": expected_wheel, "installed_target": str(installed.resolve()), "execution_root": str(ROOT.resolve()), "nonce": secrets.token_hex(32), "launcher_sha256": sha256_file(Path(__file__))}
        atomic_write_json(attestation_path, launch)
        clean_environment["HAXS_G1_LAUNCH_ATTESTATION"] = str(attestation_path)
        completed = subprocess.run([sys.executable, "-I", "scripts/run_stage5c2gR3_calibration_invariants.py"], cwd=ROOT, env=clean_environment, text=True)
        if completed.returncode != 0:
            raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
