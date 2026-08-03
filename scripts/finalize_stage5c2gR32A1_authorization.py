#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))
from stage5c2gR32A1_authorization import (
    BLOCKED_SCOPES,
    LOCK_PATH,
    RECEIPT_PATH,
    ROOT,
    assert_root_closure,
    assert_no_unlisted_runtime,
    assert_runtime_files,
    exclusive_write_json,
    load_and_validate_receipt,
    load_candidate,
    sha256_file,
    sha256_payload,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--protocol-archive", type=Path, required=True)
    parser.add_argument("--host-a", type=Path, required=True)
    parser.add_argument("--host-b", type=Path, required=True)
    parser.add_argument("--two-host-g0", type=Path, required=True)
    args = parser.parse_args()

    lock_path = ROOT / LOCK_PATH.relative_to(ROOT)
    receipt_target = ROOT / RECEIPT_PATH.relative_to(ROOT)
    if lock_path.exists() or receipt_target.exists():
        raise RuntimeError("R3.2A.1 authorization has already been finalized")
    for predecessor in [
        ROOT / "results/stage5c2gR32/protocol/LOCKED.json",
        ROOT
        / "results/stage5c2gR32/protocol/SUPERVISOR_AUTHORIZATION_G1_ONLY.json",
        ROOT / "results/stage5c2gR32A/protocol/LOCKED.json",
        ROOT
        / "results/stage5c2gR32A/protocol/SUPERVISOR_AUTHORIZATION_G1_ONLY.json",
    ]:
        if predecessor.exists():
            raise RuntimeError(f"predecessor authorization object rejected: {predecessor}")

    original_paths = {
        "protocol": args.protocol_archive,
        "host_a": args.host_a,
        "host_b": args.host_b,
        "two_host": args.two_host_g0,
        "receipt": args.receipt,
    }
    if any(
        not path.is_file() or path.is_symlink() for path in original_paths.values()
    ):
        raise RuntimeError("authorization input is missing or unsafe")
    paths = {name: path.absolute() for name, path in original_paths.items()}

    candidate = load_candidate()
    assert_runtime_files(candidate)
    assert_root_closure(candidate)
    assert_no_unlisted_runtime(candidate)
    bound_objects = {
        "wheel": candidate["wheel"],
        "environment": candidate["environment"],
        **candidate["authorization_contract"],
    }
    for name, record in bound_objects.items():
        path = ROOT / record["path"]
        if (
            not path.is_file()
            or path.is_symlink()
            or sha256_file(path) != record["sha256"]
        ):
            raise RuntimeError(f"candidate-bound authorization object failed: {name}")
    protocol_sha = sha256_file(paths["protocol"])
    host_a = json.loads(paths["host_a"].read_text(encoding="utf-8"))
    host_b = json.loads(paths["host_b"].read_text(encoding="utf-8"))
    comparison = json.loads(paths["two_host"].read_text(encoding="utf-8"))
    if (
        comparison.get("schema_version")
        != "haxs.stage5c2gR32A1.two-host-g0.v1"
        or comparison.get("status") != "PASS"
        or comparison.get("candidate_sha256") != candidate["candidate_sha256"]
        or comparison.get("host_a_sha256") != sha256_file(paths["host_a"])
        or comparison.get("host_b_sha256") != sha256_file(paths["host_b"])
        or comparison.get("physically_distinct") is not True
        or comparison.get("identity_mismatches") != []
        or comparison.get("forbidden_state") != []
        or comparison.get("G1_authorized") is not False
        or comparison.get("scientific_execution_performed") is not False
    ):
        raise RuntimeError("two-host G0 comparator identity or scope failed")
    for label, host in [("HOST_A", host_a), ("HOST_B", host_b)]:
        if (
            host.get("host_label") != label
            or host.get("status") != "PASS"
            or host.get("candidate_sha256") != candidate["candidate_sha256"]
            or host.get("protocol_archive_sha256") != protocol_sha
            or host.get("scientific_execution_performed") is not False
            or host.get("G1_authorized") is not False
        ):
            raise RuntimeError(f"{label} evidence is not an accepted current-stage G0 record")

    comparison_sha = sha256_file(paths["two_host"])
    receipt = load_and_validate_receipt(
        paths["receipt"], candidate, protocol_sha, comparison_sha
    )
    receipt_target.parent.mkdir(parents=True, exist_ok=True)
    exclusive_write_json(receipt_target, receipt)
    contracts = candidate["authorization_contract"]
    lock = {
        "schema_version": "haxs.stage5c2gR32A1.lock.v1",
        "status": "LOCKED_G1_ONLY",
        "authorized_scope": "G1_ONLY",
        "candidate_sha256": candidate["candidate_sha256"],
        "runtime_tree_sha256": candidate["runtime_tree_sha256"],
        "wheel_sha256": candidate["wheel"]["sha256"],
        "environment_sha256": candidate["environment"]["sha256"],
        "protocol_archive_sha256": protocol_sha,
        "g1_config_sha256": contracts["g1_config"]["sha256"],
        "g1_plan_sha256": contracts["g1_plan"]["sha256"],
        "unit_registry_sha256": contracts["unit_registry"]["sha256"],
        "runner_sha256": contracts["runner"]["sha256"],
        "test_ledger_sha256": contracts["test_ledger"]["sha256"],
        "root_manifest_sha256": contracts["root_manifest"]["sha256"],
        "host_a_sha256": sha256_file(paths["host_a"]),
        "host_b_sha256": sha256_file(paths["host_b"]),
        "two_host_g0_sha256": comparison_sha,
        "receipt_id": receipt["receipt_id"],
        "receipt_sha256": sha256_file(receipt_target),
        "receipt_path": receipt_target.relative_to(ROOT).as_posix(),
        "blocked_scopes": BLOCKED_SCOPES,
        "official_attempt_limit": 1,
        "same_candidate_retry_forbidden": True,
    }
    lock["lock_sha256"] = sha256_payload(lock)
    exclusive_write_json(lock_path, lock)
    print(
        json.dumps(
            {
                "status": "LOCKED_AFTER_NEW_STRUCTURED_SUPERVISORY_AUTHORIZATION",
                "candidate_sha256": candidate["candidate_sha256"],
                "receipt_id": receipt["receipt_id"],
                "authorized_scope": "G1_ONLY",
                "next": "ONE_OFFICIAL_G1_THEN_STOP",
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
