#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_stage5c2gR32A2_candidate import (
    closure_paths as predecessor_closure_paths,
    runtime_paths as predecessor_runtime_paths,
)
from stage5c2gR32A5_common import atomic_write_json, sha256_file, sha256_payload


def runtime_paths(root: Path = ROOT) -> list[Path]:
    paths = predecessor_runtime_paths(root)
    paths.extend([
        root / "scripts/package_stage5c2gR32A4_host_b_release.py",
        root / "scripts/package_stage5c2gR32A4_supervisor_return.py",
        root / "scripts/dry_run_stage5c2gR32A4_complete_return.py",
        root / "ci/run_stage5c2gR32A4_github_host_b_g0.sh",
        root / ".github/workflows/stage5c2gR32A4-host-b-g0.yml",
        root / "run_stage5c2gR32A5_G0.sh",
        root / "ci/run_stage5c2gR32A5_g0.sh",
        root / "ci/run_stage5c2gR32A5_github_host_b_g0.sh",
        root / ".github/workflows/stage5c2gR32A5-host-b-g0.yml",
    ])
    return sorted(set(paths))


def closure_paths(root: Path = ROOT) -> list[Path]:
    paths = predecessor_closure_paths(root)
    paths.extend([
        root / "results/stage5c2gR32A3/protocol/CANDIDATE.json",
        root / "output/stage5c2gR32A3/HAXS_Stage5C2G_R3_2A_3_Protocol.zip",
        root / "output/stage5c2gR32A3/HAXS_Stage5C2G_R3_2A_3_Protocol_SHA256.txt",
        root / "results/stage5c2gR32A4/protocol/CANDIDATE.json",
        root / "output/stage5c2gR32A4/HAXS_Stage5C2G_R3_2A_4_Protocol.zip",
        root / "output/stage5c2gR32A4/HAXS_Stage5C2G_R3_2A_4_Protocol_SHA256.txt",
    ])
    if any(not path.is_file() or path.is_symlink() for path in paths):
        raise RuntimeError("required A4 predecessor custody is missing or unsafe")
    return sorted(set(paths))


def bound(path: Path) -> dict:
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256_file(path)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fail-closed", action="store_true", required=True)
    parser.add_argument("--out", type=Path, default=ROOT / "results/stage5c2gR32A5/protocol/CANDIDATE.json")
    args = parser.parse_args()
    if args.out.exists() or args.out.is_symlink():
        raise RuntimeError("refusing to overwrite R3.2A.5 candidate")
    wheel = ROOT / "output/stage5c2gR32A5/haxs-0.8.8-py3-none-any.whl"
    environment = ROOT / "results/stage5c2gR32A5/environment.json"
    contracts = {
        "receipt_template": ROOT / "configs/stage5c2gR32A5/structured_receipt_template.json",
        "finalizer": ROOT / "scripts/finalize_stage5c2gR32A5_authorization.py",
        "comparator": ROOT / "scripts/compare_stage5c2gR32A5_g0_hosts.py",
        "root_verifier": ROOT / "scripts/verify_stage5c2gR32A5_root.py",
        "environment_verifier": ROOT / "scripts/verify_stage5c2gR32A5_environment.py",
        "launcher": ROOT / "scripts/launch_stage5c2gR32A5_G1_isolated.py",
        "runner": ROOT / "scripts/run_stage5c2gR32A5_G1.py",
        "g1_config": ROOT / "configs/stage5c2gR32A/g1_deterministic.yaml",
        "g1_plan": ROOT / "output/stage5c2gR32A/g1_preflight/quadrature_node_registry.csv",
        "unit_registry": ROOT / "output/stage5c2gR32A/g1_preflight/unit_registry.csv",
        "test_ledger": ROOT / "results/stage5c2gR32A5/protocol/NAMED_TEST_LEDGER.json",
        "adversarial_outcomes": ROOT / "results/stage5c2gR32A5/adversarial/OUTCOMES.json",
        "root_manifest": ROOT / "results/stage5c2gR32A5/protocol/IMMUTABLE_ROOT_MANIFEST.json",
        "control_plane_schema": ROOT / "configs/stage5c2gR32A5/control_plane.json",
        "supersession_ledger": ROOT / "configs/stage5c2gR32A5/supersession.json",
        "production_semantics": ROOT / "scripts/stage5c2gR32A5_semantics.py",
        "production_g0_writer": ROOT / "scripts/run_stage5c2gR32A5_g0.py",
        "host_b_release_packager": ROOT / "scripts/package_stage5c2gR32A5_host_b_release.py",
        "complete_return_packager": ROOT / "scripts/package_stage5c2gR32A5_supervisor_return.py",
        "local_two_host_dry_run": ROOT / "scripts/dry_run_stage5c2gR32A5_complete_return.py",
        "local_complete_lifecycle": ROOT / "scripts/run_stage5c2gR32A5_local_complete_cycle.py",
        "engineering_acceptance_contract": ROOT / "docs/stage5c2gR32A5/ACCEPTANCE_CONTRACT.md",
        "authoritative_runbook": ROOT / "docs/stage5c2gR32A5/STAGE5C2GR32A5_RUNBOOK.md",
        "failure_boundary_protocol": ROOT / "docs/stage5c3VB/PROTOCOL.md",
        "failure_boundary_config": ROOT / "configs/stage5c3VB/protocol.yaml",
        "host_b_workflow": ROOT / ".github/workflows/stage5c2gR32A5-host-b-g0.yml",
        "host_b_runner": ROOT / "ci/run_stage5c2gR32A5_github_host_b_g0.sh",
    }
    dependency_lock = ROOT / "requirements-stage5c2gR3.lock"
    wheelhouse = ROOT / "ci/frozen/stage5c2gR32A2/WHEELHOUSE_MANIFEST_SHA256.txt"
    required = [wheel, environment, dependency_lock, wheelhouse, *contracts.values()]
    if any(not path.is_file() or path.is_symlink() for path in required):
        raise RuntimeError("R3.2A.5 candidate input is missing or unsafe")
    runtime = {path.relative_to(ROOT).as_posix(): sha256_file(path) for path in runtime_paths()}
    closure = {path.relative_to(ROOT).as_posix(): sha256_file(path) for path in closure_paths()}
    contract_records = {name: bound(path) for name, path in contracts.items()}
    protocol_content = {
        "runtime_tree_sha256": sha256_payload(runtime),
        "root_closure_sha256": sha256_payload(closure),
        "authorization_contract_sha256": sha256_payload(contract_records),
    }
    payload = {
        "schema_version": "haxs.stage5c2gR32A5.candidate.v1",
        "stage": "stage5c2gR32A5",
        "predecessor_candidate_sha256": "0fe6d37617d02abfc14a1bd6c58b580452205a69f3ebc4039c481097bcda9b9d",
        "predecessor_disposition": "PRESERVED_PHASE_A_EVIDENCE_NOT_AUTHORIZATION_EXECUTABLE",
        "runtime_files": runtime, "runtime_tree_sha256": protocol_content["runtime_tree_sha256"],
        "root_closure_files": closure, "root_closure_sha256": protocol_content["root_closure_sha256"],
        "protocol_content_sha256": sha256_payload(protocol_content),
        "python_executable_sha256": json.loads(environment.read_text())["python_executable_sha256"],
        "wheel": bound(wheel), "environment": bound(environment),
        "dependency_lock": bound(dependency_lock), "wheelhouse_manifest": bound(wheelhouse),
        "authorization_contract": contract_records,
        "scope": {
            "scientific_G1_design": "UNCHANGED_FROM_R3_2A_4",
            "immutable_root_policy": "BYTE_IDENTICAL_DENY_BY_DEFAULT_NO_CONTROL_STATE",
            "control_plane_policy": "EXTERNAL_CANDIDATE_NAMESPACE_EXACT_MEMBERSHIP_SINGLE_WRITER",
            "lifecycle_policy": "RECEIPT_TO_RUNNER_STUB_COMPLETE_BEFORE_EXTERNAL_G0",
            "junit_policy": "EXACT_ORDERED_NODEID_AND_CANONICAL_PRODUCTION_TARGET",
            "command_policy": "WRITER_GENERATED_STRUCTURED_EXACT_ARGV_ZERO_EXIT_JUNIT_BOUND",
            "protocol_policy": "ACTUAL_ARCHIVE_SHA_REQUIRED_AT_HOST_AND_FINALIZER",
            "return_policy": "ZIP_ONLY_COMPLETE_SELF_CONTAINED_RETURN",
            "local_gate": "SYNTHETIC_TWO_HOST_COMPLETE_RETURN_REQUIRED_BEFORE_EXTERNAL_G0",
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
