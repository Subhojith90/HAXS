#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path

from stage5c2gR32_common import atomic_write_json, sha256_payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host-a", required=True, type=Path)
    parser.add_argument("--host-b", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    a = json.loads(args.host_a.read_text(encoding="utf-8"))
    b = json.loads(args.host_b.read_text(encoding="utf-8"))
    identities = [
        "candidate_sha256",
        "runtime_tree_sha256",
        "wheel_sha256",
        "protocol_archive_sha256",
    ]
    checks = {
        "both_passed": a.get("status") == b.get("status") == "PASS",
        "different_host_tags": a.get("host_tag") != b.get("host_tag"),
        "different_physical_hosts": a["physical_host"]["physical_host_sha256"]
        != b["physical_host"]["physical_host_sha256"],
        "frozen_identities_match": all(a.get(key) == b.get(key) for key in identities),
        "no_scientific_execution": a.get("scientific_execution_performed") is False
        and b.get("scientific_execution_performed") is False,
    }
    payload = {
        "schema_version": "haxs.stage5c2gR32.two-host-g0.v1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "host_a": a,
        "host_b": b,
        "next": "RETURN_FOR_SUPERVISORY_ACCEPTANCE_BEFORE_NEW_RECEIPT",
    }
    payload["comparison_sha256"] = sha256_payload(payload)
    atomic_write_json(args.out, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    if payload["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
