#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def physical_identity() -> dict:
    values = []
    if platform.system() == "Darwin":
        result = subprocess.run(
            ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
            text=True,
            capture_output=True,
            check=True,
        ).stdout
        for key in ["IOPlatformUUID", "IOPlatformSerialNumber"]:
            match = re.search(rf'"{key}"\s*=\s*"([^"]+)"', result)
            if not match:
                raise RuntimeError(f"physical host field unavailable: {key}")
            values.append(match.group(1))
    else:
        machine_id = Path("/etc/machine-id")
        if not machine_id.is_file():
            raise RuntimeError("physical host identity unavailable")
        values = [machine_id.read_text(encoding="utf-8").strip(), platform.node()]
    return {
        "system": platform.system(),
        "machine": platform.machine(),
        "platform_identity_sha256": hashlib.sha256(values[0].encode()).hexdigest(),
        "serial_or_node_sha256": hashlib.sha256(values[1].encode()).hexdigest(),
    }


def run(command: list[str], transcript: Path) -> None:
    environment = os.environ.copy()
    for key in ["PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP", "PYTHONINSPECT", "PYTHONUSERBASE", "LD_PRELOAD", "DYLD_INSERT_LIBRARIES", "DYLD_LIBRARY_PATH"]:
        environment.pop(key, None)
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
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
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if sys.version_info[:3] != (3, 12, 7):
        raise RuntimeError("G0 requires CPython 3.12.7")
    candidate_path = ROOT / "results/stage5c2gR32A/protocol/CANDIDATE.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    mismatches = [
        relative
        for relative, expected in candidate["runtime_files"].items()
        if not (ROOT / relative).is_file() or sha256(ROOT / relative) != expected
    ]
    if mismatches:
        raise RuntimeError(f"candidate runtime mismatch: {mismatches[:5]}")
    transcript_dir = args.out.parent / f"{args.host_label}_transcripts"
    if args.out.exists() or transcript_dir.exists():
        raise RuntimeError("refusing to overwrite G0 host evidence")
    transcript_dir.mkdir(parents=True)
    commands = [
        ([sys.executable, "-m", "compileall", "-q", "src", "scripts", "scripts_patch", "tests"], "00_compileall.txt"),
        ([sys.executable, "-m", "pytest", "-q"], "01_full_tests.txt"),
        ([sys.executable, "-m", "pytest", "-q", "tests/stage5c2gR32A", "tests/stage5c2gR32", "tests/regression"], "02_targeted_tests.txt"),
        ([sys.executable, "-I", "scripts/verify_stage5c2gR32A_immutable_install.py"], "03_immutable_install.txt"),
        ([sys.executable, "-I", "scripts/verify_stage5c2gR32A_fresh_unzip.py", "--submission", "output/stage5c2gR32A/HAXS_Stage5C2G_R3_2A_Protocol.zip"], "04_fresh_unzip.txt"),
    ]
    for command, name in commands:
        run(command, transcript_dir / name)
    transcript_hashes = {
        path.name: sha256(path) for path in sorted(transcript_dir.iterdir()) if path.is_file()
    }
    payload = {
        "schema_version": "haxs.stage5c2gR32A.physical-host-g0.v1",
        "status": "PASS",
        "host_label": args.host_label,
        "candidate_sha256": candidate["candidate_sha256"],
        "runtime_tree_sha256": candidate["runtime_tree_sha256"],
        "wheel_sha256": candidate["wheel"]["sha256"],
        "environment_sha256": candidate["environment"]["sha256"],
        "protocol_archive_sha256": sha256(ROOT / "output/stage5c2gR32A/HAXS_Stage5C2G_R3_2A_Protocol.zip"),
        "python_version": platform.python_version(),
        "physical_host": physical_identity(),
        "transcript_sha256": transcript_hashes,
        "scientific_execution_performed": False,
        "G1_authorized": False,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
