#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host-a", type=Path, required=True)
    parser.add_argument("--host-b", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    hosts = [json.loads(args.host_a.read_text()), json.loads(args.host_b.read_text())]
    if {host.get("host_label") for host in hosts} != {"HOST_A", "HOST_B"}:
        raise RuntimeError("G0 host labels are incomplete")
    if any(host.get("status") != "PASS" for host in hosts):
        raise RuntimeError("both G0 hosts must pass")
    identity_fields = ["candidate_sha256", "runtime_tree_sha256", "wheel_sha256", "environment_sha256", "protocol_archive_sha256"]
    mismatches = [field for field in identity_fields if hosts[0][field] != hosts[1][field]]
    physical_a = hosts[0]["physical_host"]
    physical_b = hosts[1]["physical_host"]
    physically_distinct = (
        physical_a["platform_identity_sha256"] != physical_b["platform_identity_sha256"]
        and physical_a["serial_or_node_sha256"] != physical_b["serial_or_node_sha256"]
    )
    if mismatches or not physically_distinct:
        raise RuntimeError(f"two-host G0 mismatch={mismatches} physically_distinct={physically_distinct}")
    payload = {
        "schema_version": "haxs.stage5c2gR32A.two-host-g0.v1",
        "status": "PASS",
        "candidate_sha256": hosts[0]["candidate_sha256"],
        "physically_distinct": True,
        "identity_mismatches": [],
        "next": "SUPERVISORY_ACCEPTANCE_AND_NEW_G1_ONLY_RECEIPT",
        "G1_authorized": False,
    }
    if args.out.exists():
        raise RuntimeError("refusing to overwrite two-host comparison")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
