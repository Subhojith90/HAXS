#!/usr/bin/env python
from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2gR32_common import atomic_write_json, sha256_file, sha256_payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "results/stage5c2gR32A/environment.json")
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError("R3.2A requires CPython 3.12")
    packages = {}
    for name in ["numpy", "pandas", "scipy", "PyYAML", "matplotlib", "pytest", "setuptools", "wheel", "pip"]:
        packages[name] = importlib.metadata.version(name)
    payload = {
        "schema_version": "haxs.stage5c2gR32A.environment.v1",
        "implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "python_executable_name": Path(sys.executable).name,
        "python_executable_sha256": sha256_file(sys.executable),
        "platform_system": platform.system(),
        "platform_machine": platform.machine(),
        "packages": packages,
        "dependency_lock": {
            "path": "requirements-stage5c2gR3.lock",
            "sha256": sha256_file(ROOT / "requirements-stage5c2gR3.lock"),
        },
        "absolute_paths_recorded": False,
    }
    payload["environment_sha256"] = sha256_payload(payload)
    atomic_write_json(args.out, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
