#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2gR3_common import require_isolated_interpreter

REQUIRED = {"schema_version", "host_label", "attested_at_utc", "physical_host", "candidate_sha256", "runtime_tree_sha256", "wheel_sha256", "protocol_archive_sha256", "canonical_config_hashes", "expected_plan_hashes", "environment_spec", "g0_status", "scientific_execution_performed", "authoritative_g0_transcript_sha256"}


def _read(path: str) -> dict:
    candidate = Path(path)
    if not candidate.is_file() or candidate.is_symlink(): raise RuntimeError(f"unsafe or missing host attestation: {path}")
    payload = json.loads(candidate.read_text(encoding="utf-8"))
    if set(payload) != REQUIRED or payload["schema_version"] != "haxs.stage5c2gR3.1.physical-host.v1": raise RuntimeError("physical-host attestation schema failed")
    if payload["g0_status"] != "PASS" or payload["scientific_execution_performed"] is not False: raise RuntimeError("host attestation is not a pre-execution G0 pass")
    if set(payload["physical_host"]) != {"platform_uuid_sha256", "serial_number_sha256", "system", "machine"}: raise RuntimeError("physical-host identity schema failed")
    hashes = [payload["candidate_sha256"], payload["runtime_tree_sha256"], payload["wheel_sha256"], payload["protocol_archive_sha256"], payload["physical_host"]["platform_uuid_sha256"], payload["physical_host"]["serial_number_sha256"], *payload["canonical_config_hashes"].values(), *payload["expected_plan_hashes"].values(), *payload["authoritative_g0_transcript_sha256"].values()]
    if any(not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value) for value in hashes): raise RuntimeError("physical-host attestation contains a malformed SHA-256")
    if set(payload["authoritative_g0_transcript_sha256"]) != {"00_compileall.txt", "01_static_gate.txt", "02_full_tests.txt", "03_targeted_tests.txt", "04_immutable_install.txt", "05_candidate.txt", "06_package.txt", "07_fresh_unzip.txt"}: raise RuntimeError("physical-host attestation transcript schema failed")
    try: issued = datetime.fromisoformat(str(payload["attested_at_utc"]).replace("Z", "+00:00"))
    except ValueError as error: raise RuntimeError("physical-host attestation time failed") from error
    if issued.tzinfo is None or issued.utcoffset() is None or issued.utcoffset().total_seconds() != 0: raise RuntimeError("physical-host attestation time must be UTC")
    return payload


def verify_two_hosts(host_a: str, host_b: str) -> dict:
    a, b = _read(host_a), _read(host_b)
    if {a["host_label"], b["host_label"]} != {"HOST_A", "HOST_B"}: raise RuntimeError("attestations must contain exactly HOST_A and HOST_B")
    for field in ["candidate_sha256", "runtime_tree_sha256", "wheel_sha256", "protocol_archive_sha256", "canonical_config_hashes", "expected_plan_hashes", "environment_spec"]:
        if a[field] != b[field]: raise RuntimeError(f"two-host candidate identity mismatch: {field}")
    for field in ["platform_uuid_sha256", "serial_number_sha256"]:
        if a["physical_host"][field] == b["physical_host"][field]: raise RuntimeError("G0 hosts are not physically distinct")
    return {"stage": "stage5c2gR3_1_two_physical_host_gate", "status": "PASS", "candidate_sha256": a["candidate_sha256"], "wheel_sha256": a["wheel_sha256"], "protocol_archive_sha256": a["protocol_archive_sha256"], "distinct_platform_uuid": True, "distinct_serial_number": True}


def main() -> None:
    require_isolated_interpreter(ROOT)
    parser = argparse.ArgumentParser(); parser.add_argument("--host-a", required=True); parser.add_argument("--host-b", required=True); args = parser.parse_args()
    print(json.dumps(verify_two_hosts(args.host_a, args.host_b), indent=2))


if __name__ == "__main__": main()
