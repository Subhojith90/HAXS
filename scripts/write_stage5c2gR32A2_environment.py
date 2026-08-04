#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2gR32A2_common import atomic_write_json, sha256_file, sha256_payload
from verify_stage5c2gR32A2_environment import current_environment, installed_wheel_tree_identity


def installed_tree(wheel: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix="haxs-stage5c2gR32A2-env-") as directory:
        target = Path(directory) / "site"
        clean = {key: value for key, value in os.environ.items() if not key.startswith("PYTHON")}
        completed = subprocess.run(
            [sys.executable, "-I", "-m", "pip", "install", "--no-index", "--no-deps", "--no-compile", "--target", str(target), str(wheel)],
            cwd=directory, env=clean, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        if completed.returncode:
            raise RuntimeError("immutable wheel install failed while building environment attestation")
        return installed_wheel_tree_identity(target, wheel)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "results/stage5c2gR32A2/environment.json")
    args = parser.parse_args()
    if not sys.flags.isolated or sys.flags.no_user_site != 1:
        raise RuntimeError("environment writer requires isolated Python (-I)")
    if sys.version_info[:3] != (3, 12, 7) or platform.python_implementation() != "CPython":
        raise RuntimeError("R3.2A.2 requires exact CPython 3.12.7")
    if args.out.exists() or args.out.is_symlink():
        raise RuntimeError("refusing to overwrite environment attestation")
    wheel = ROOT / "output/stage5c2gR32A2/haxs-0.8.5-py3-none-any.whl"
    lock = ROOT / "requirements-stage5c2gR3.lock"
    wheelhouse = ROOT / "ci/frozen/stage5c2gR32A2/WHEELHOUSE_MANIFEST_SHA256.txt"
    if any(not path.is_file() or path.is_symlink() for path in [wheel, lock, wheelhouse]):
        raise RuntimeError("wheel, dependency lock, or wheelhouse manifest is missing")
    installed = installed_tree(wheel)
    payload = {
        "schema_version": "haxs.stage5c2gR32A2.environment.v1",
        **current_environment(),
        "haxs_version": "0.8.5",
        "dependency_lock": {"path": lock.relative_to(ROOT).as_posix(), "sha256": sha256_file(lock)},
        "wheelhouse_manifest": {"path": wheelhouse.relative_to(ROOT).as_posix(), "sha256": sha256_file(wheelhouse)},
        "installed_wheel_tree_sha256": installed["payload_tree_sha256"],
        "installed_wheel_payload_files": installed["payload_files"],
        "generated_install_metadata_policy": installed["generated_metadata_policy"],
        "thread_environment": {
            "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
            "VECLIB_MAXIMUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1",
        },
        "absolute_paths_recorded": False,
    }
    payload["environment_sha256"] = sha256_payload(payload)
    atomic_write_json(args.out, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
