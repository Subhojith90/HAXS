#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2gR32A1_authorization import atomic_write_json, sha256_file

IDENTITY_FIELDS = [
    "candidate_sha256",
    "runtime_tree_sha256",
    "wheel_sha256",
    "environment_sha256",
    "protocol_archive_sha256",
    "g1_config_sha256",
    "g1_plan_sha256",
    "unit_registry_sha256",
    "runner_sha256",
    "test_ledger_sha256",
    "root_manifest_sha256",
]


def compare(host_a_path: Path, host_b_path: Path) -> dict:
    if any(
        not path.is_file() or path.is_symlink()
        for path in [host_a_path, host_b_path]
    ):
        raise RuntimeError("G0 host record is missing or unsafe")
    host_a = json.loads(host_a_path.read_text(encoding="utf-8"))
    host_b = json.loads(host_b_path.read_text(encoding="utf-8"))
    if host_a.get("host_label") != "HOST_A" or host_b.get("host_label") != "HOST_B":
        raise RuntimeError("G0 host labels are not exact")
    if (
        host_a.get("schema_version")
        != "haxs.stage5c2gR32A1.physical-host-g0.v1"
        or host_b.get("schema_version")
        != "haxs.stage5c2gR32A1.physical-host-g0.v1"
        or host_a.get("status") != "PASS"
        or host_b.get("status") != "PASS"
    ):
        raise RuntimeError("both current-stage G0 host records must pass")
    mismatches = [
        field for field in IDENTITY_FIELDS if host_a.get(field) != host_b.get(field)
    ]
    physical_a = host_a["physical_host"]
    physical_b = host_b["physical_host"]
    physically_distinct = (
        physical_a["platform_identity_sha256"]
        != physical_b["platform_identity_sha256"]
        and physical_a["serial_or_node_sha256"]
        != physical_b["serial_or_node_sha256"]
    )
    forbidden = [
        host["host_label"]
        for host in [host_a, host_b]
        if host.get("scientific_execution_performed") is not False
        or host.get("G1_authorized") is not False
    ]
    if mismatches or not physically_distinct or forbidden:
        raise RuntimeError(
            "two-host G0 failed: "
            f"mismatches={mismatches} distinct={physically_distinct} forbidden={forbidden}"
        )
    return {
        "schema_version": "haxs.stage5c2gR32A1.two-host-g0.v1",
        "status": "PASS",
        "candidate_sha256": host_a["candidate_sha256"],
        "host_a_sha256": sha256_file(host_a_path),
        "host_b_sha256": sha256_file(host_b_path),
        "physically_distinct": True,
        "identity_mismatches": [],
        "forbidden_state": [],
        "G1_authorized": False,
        "scientific_execution_performed": False,
        "next": "SUPERVISORY_REVIEW_BEFORE_NEW_G1_ONLY_RECEIPT",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host-a", type=Path, required=True)
    parser.add_argument("--host-b", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists() or args.out.is_symlink():
        raise RuntimeError("refusing to overwrite two-host G0 comparison")
    payload = compare(args.host_a.resolve(), args.host_b.resolve())
    atomic_write_json(args.out, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
