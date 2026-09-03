#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_stage5c2gR32A2_candidate import closure_paths, runtime_paths as predecessor_runtime_paths
from stage5c2gR32A3_common import atomic_write_json, sha256_file, sha256_payload


def runtime_paths(root: Path = ROOT) -> list[Path]:
    paths = predecessor_runtime_paths(root)
    paths.append(root / "run_stage5c2gR32A3_G0.sh")
    return sorted(set(paths))


def bound(path: Path) -> dict:
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256_file(path)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fail-closed", action="store_true", required=True)
    parser.add_argument("--out", type=Path, default=ROOT / "results/stage5c2gR32A3/protocol/CANDIDATE.json")
    args = parser.parse_args()
    if args.out.exists() or args.out.is_symlink():
        raise RuntimeError("refusing to overwrite R3.2A.3 candidate")
    wheel = ROOT / "output/stage5c2gR32A3/haxs-0.8.6-py3-none-any.whl"
    environment = ROOT / "results/stage5c2gR32A3/environment.json"
    contracts = {
        "receipt_template": ROOT / "configs/stage5c2gR32A3/structured_receipt_template.json",
        "finalizer": ROOT / "scripts/finalize_stage5c2gR32A3_authorization.py",
        "comparator": ROOT / "scripts/compare_stage5c2gR32A3_g0_hosts.py",
        "root_verifier": ROOT / "scripts/verify_stage5c2gR32A3_root.py",
        "environment_verifier": ROOT / "scripts/verify_stage5c2gR32A3_environment.py",
        "launcher": ROOT / "scripts/launch_stage5c2gR32A3_G1_isolated.py",
        "runner": ROOT / "scripts/run_stage5c2gR32A3_G1.py",
        "g1_config": ROOT / "configs/stage5c2gR32A/g1_deterministic.yaml",
        "g1_plan": ROOT / "output/stage5c2gR32A/g1_preflight/quadrature_node_registry.csv",
        "unit_registry": ROOT / "output/stage5c2gR32A/g1_preflight/unit_registry.csv",
        "test_ledger": ROOT / "results/stage5c2gR32A3/protocol/NAMED_TEST_LEDGER.json",
        "adversarial_outcomes": ROOT / "results/stage5c2gR32A3/adversarial/OUTCOMES.json",
        "root_manifest": ROOT / "results/stage5c2gR32A3/protocol/ROOT_MANIFEST.json",
        "supersession_ledger": ROOT / "configs/stage5c2gR32A3/supersession.json",
    }
    dependency_lock = ROOT / "requirements-stage5c2gR3.lock"
    wheelhouse = ROOT / "ci/frozen/stage5c2gR32A2/WHEELHOUSE_MANIFEST_SHA256.txt"
    required = [wheel, environment, dependency_lock, wheelhouse, *contracts.values()]
    if any(not path.is_file() or path.is_symlink() for path in required):
        raise RuntimeError("R3.2A.3 candidate input is missing or unsafe")
    runtime = {path.relative_to(ROOT).as_posix(): sha256_file(path) for path in runtime_paths()}
    closure = {path.relative_to(ROOT).as_posix(): sha256_file(path) for path in closure_paths()}
    contract_records = {name: bound(path) for name, path in contracts.items()}
    protocol_content = {
        "runtime_tree_sha256": sha256_payload(runtime),
        "root_closure_sha256": sha256_payload(closure),
        "authorization_contract_sha256": sha256_payload(contract_records),
    }
    payload = {
        "schema_version": "haxs.stage5c2gR32A3.candidate.v1",
        "stage": "stage5c2gR32A3",
        "predecessor_candidate_sha256": "24d6d3eb09b41feef6ef8858a300fc0ecbc9c9cf562bdc363d370ff528f2c9a4",
        "predecessor_disposition": "PRESERVED_PROVISIONAL_G0_RECEIPT_PERMANENTLY_REJECTED",
        "runtime_files": runtime, "runtime_tree_sha256": protocol_content["runtime_tree_sha256"],
        "root_closure_files": closure, "root_closure_sha256": protocol_content["root_closure_sha256"],
        "protocol_content_sha256": sha256_payload(protocol_content),
        "python_executable_sha256": json.loads(environment.read_text())["python_executable_sha256"],
        "wheel": bound(wheel), "environment": bound(environment),
        "dependency_lock": bound(dependency_lock), "wheelhouse_manifest": bound(wheelhouse),
        "authorization_contract": contract_records,
        "scope": {
            "scientific_G1_design": "UNCHANGED_FROM_R3_2A_2",
            "junit_policy": "EXACT_ORDERED_NODEID_EQUALITY",
            "command_policy": "STRUCTURED_EXACT_ARGV_ZERO_EXIT_JUNIT_BOUND",
            "protocol_policy": "ACTUAL_ARCHIVE_SHA_REQUIRED_AT_HOST_AND_FINALIZER",
        },
        "execution_permissions": {
            "G1": "BLOCKED_PENDING_NEW_SUPERVISORY_REVIEW_AND_RECEIPT",
            "G2": "BLOCKED", "G3": "BLOCKED", "G4": "BLOCKED",
            "STAGE5C3": "BLOCKED", "STAGE5D": "BLOCKED",
            "MANUSCRIPT_RESULT_CLAIMS": "BLOCKED",
            "EXACT_MOBILE_HOLE_CLAIMS": "BLOCKED", "PUBLIC_RELEASE": "BLOCKED",
        },
    }
    payload["candidate_sha256"] = sha256_payload(payload)
    atomic_write_json(args.out, payload)
    print(json.dumps({
        "status": "AWAITING_REPLACEMENT_TWO_PHYSICAL_HOST_G0",
        "candidate_sha256": payload["candidate_sha256"],
        "protocol_content_sha256": payload["protocol_content_sha256"],
        "runtime_files": len(runtime), "root_closure_files": len(closure),
        "scientific_execution_performed": False, "G1_authorized": False,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
