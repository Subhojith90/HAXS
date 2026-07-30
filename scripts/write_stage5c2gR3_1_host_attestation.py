#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2gR3_common import CANDIDATE_PATH, INSTALLED_WHEEL_PATH, require_isolated_interpreter, sha256_file
from stage5c2gR3_state import atomic_write_json

G0_TRANSCRIPTS = ["00_compileall.txt", "01_static_gate.txt", "02_full_tests.txt", "03_targeted_tests.txt", "04_immutable_install.txt", "05_candidate.txt", "06_package.txt", "07_fresh_unzip.txt"]


def _hardware_values() -> tuple[str, str]:
    completed = subprocess.run(
        ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise RuntimeError("physical-host attestation requires macOS ioreg")
    uuid_match = re.search(r'"IOPlatformUUID"\s*=\s*"([^\"]+)"', completed.stdout)
    serial_match = re.search(r'"IOPlatformSerialNumber"\s*=\s*"([^\"]+)"', completed.stdout)
    if not uuid_match or not serial_match:
        raise RuntimeError("physical-host UUID or serial number is unavailable")
    return uuid_match.group(1), serial_match.group(1)


def _digest(value: str) -> str:
    return hashlib.sha256(("HAXS_STAGE5C2GR3_1_HOST_ID\0" + value).encode()).hexdigest()


def main() -> None:
    require_isolated_interpreter(ROOT)
    parser = argparse.ArgumentParser()
    parser.add_argument("--host-label", required=True, choices=["HOST_A", "HOST_B"])
    parser.add_argument("--transcript-dir", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    candidate_path = ROOT / CANDIDATE_PATH
    if not candidate_path.is_file() or candidate_path.is_symlink():
        raise RuntimeError("candidate must be reconstructed before host attestation")
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    wheel = ROOT / INSTALLED_WHEEL_PATH
    if not wheel.is_file() or sha256_file(wheel) != candidate["installed_wheel"]["wheel_sha256"]:
        raise RuntimeError("candidate-bound installed wheel is missing or changed")
    transcript_root = Path(args.transcript_dir)
    if not transcript_root.is_absolute(): transcript_root = ROOT / transcript_root
    transcripts = {name: transcript_root / name for name in G0_TRANSCRIPTS}
    if any(not path.is_file() or path.is_symlink() or path.stat().st_size == 0 for path in transcripts.values()):
        raise RuntimeError("final G0 transcript set is incomplete")
    markers = {"00_compileall.txt": "COMPILEALL_STATUS=PASS", "01_static_gate.txt": '"status": "PASS"', "02_full_tests.txt": "passed", "03_targeted_tests.txt": "passed", "04_immutable_install.txt": '"status": "PASS"', "05_candidate.txt": "candidate_sha256", "06_package.txt": "candidate_sha256", "07_fresh_unzip.txt": '"status": "PASS"'}
    for name, marker in markers.items():
        if marker not in transcripts[name].read_text(encoding="utf-8", errors="replace"):
            raise RuntimeError(f"final G0 transcript lacks its success marker: {name}")
    archive = ROOT / "output/stage5c2gR3/HAXS_Stage5C2G_R3_1_Protocol.zip"
    if not archive.is_file() or archive.is_symlink(): raise RuntimeError("final protocol archive is missing")
    platform_uuid, serial = _hardware_values()
    payload = {
        "schema_version": "haxs.stage5c2gR3.1.physical-host.v1",
        "host_label": args.host_label,
        "attested_at_utc": datetime.now(timezone.utc).isoformat(),
        "physical_host": {
            "platform_uuid_sha256": _digest(platform_uuid),
            "serial_number_sha256": _digest(serial),
            "system": platform.system(),
            "machine": platform.machine(),
        },
        "candidate_sha256": candidate["candidate_sha256"],
        "runtime_tree_sha256": candidate["runtime_tree_sha256"],
        "wheel_sha256": candidate["installed_wheel"]["wheel_sha256"],
        "protocol_archive_sha256": sha256_file(archive),
        "canonical_config_hashes": {gate: value["sha256"] for gate, value in candidate["canonical_configs"].items()},
        "expected_plan_hashes": {gate: value["sha256"] for gate, value in candidate["expected_plans"].items()},
        "environment_spec": candidate["environment"]["spec"],
        "g0_status": "PASS",
        "scientific_execution_performed": False,
        "authoritative_g0_transcript_sha256": {name: sha256_file(path) for name, path in transcripts.items()},
    }
    target = Path(args.out)
    if not target.is_absolute(): target = ROOT / target
    atomic_write_json(target, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__": main()
