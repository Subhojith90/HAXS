#!/usr/bin/env python
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WHEEL = ROOT / "output/stage5c2gR32A1/haxs-0.8.4-py3-none-any.whl"


def tree_digest() -> str:
    digest = hashlib.sha256()
    for path in sorted((ROOT / "src/haxs").rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            digest.update(path.relative_to(ROOT).as_posix().encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


def main() -> None:
    if sys.version_info[:3] != (3, 12, 7):
        raise RuntimeError("immutable install check requires exact CPython 3.12.7")
    if not WHEEL.is_file() or WHEEL.is_symlink():
        raise RuntimeError("R3.2A.1 immutable wheel is missing or unsafe")
    before = tree_digest()
    with tempfile.TemporaryDirectory(prefix="haxs-r32a1-install-") as directory:
        target = Path(directory) / "site"
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
                str(target),
                str(WHEEL),
            ],
            cwd="/tmp",
            env={
                key: value
                for key, value in os.environ.items()
                if key
                not in {
                    "PYTHONPATH",
                    "PYTHONHOME",
                    "PYTHONSTARTUP",
                    "PYTHONINSPECT",
                    "PYTHONUSERBASE",
                }
            },
            text=True,
            capture_output=True,
        )
        if completed.returncode:
            raise RuntimeError(completed.stdout + completed.stderr)
        probe = subprocess.run(
            [
                sys.executable,
                "-I",
                "-c",
                "import json,sys; sys.path.insert(0,sys.argv[1]); import haxs; "
                "print(json.dumps({'version':haxs.__version__,'origin':haxs.__file__}))",
                str(target),
            ],
            cwd="/tmp",
            text=True,
            capture_output=True,
            check=True,
        )
        result = json.loads(probe.stdout)
        if result["version"] != "0.8.4" or not Path(
            result["origin"]
        ).is_relative_to(target):
            raise RuntimeError("isolated interpreter did not import the R3.2A.1 wheel")
    after = tree_digest()
    if before != after:
        raise RuntimeError("wheel installation mutated the source tree")
    print(
        json.dumps(
            {
                "stage": "stage5c2gR32A1_immutable_install",
                "status": "PASS",
                "source_tree_before_sha256": before,
                "source_tree_after_sha256": after,
                "wheel_sha256": hashlib.sha256(WHEEL.read_bytes()).hexdigest(),
                "installed_version": "0.8.4",
                "isolated": True,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
