#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2gR32A2_common import atomic_write_json, sha256_file, sha256_payload

TEXT_SUFFIXES = {".py", ".yaml", ".yml", ".json", ".md", ".sh", ".txt", ".csv", ".toml", ".lock"}
ROOT_CONTRACTS = [
    "README.md", "STAGE3_COMMANDS.sh", "STAGE3A_COMMANDS.sh", "STAGE5C2GR3_COMMANDS.sh",
    "STAGE5C2GR32_COMMANDS.sh", "pyproject.toml", "requirements-stage5c2gR2.lock",
    "requirements-stage5c2gR3.in", "requirements-stage5c2gR3.lock", "run_stage5c2gR32A2_G0.sh",
    "ci/frozen/stage5c2gR32A2/WHEELHOUSE_MANIFEST_SHA256.txt",
]
CUSTODY_PATHS = [
    "results/stage5c2d_lite/confirmation/stage5c2d_block_manifest.json",
    "results/stage5c2d_lite/confirmation/stage5c2d_curves_all.csv",
    "results/stage5c2d_lite/confirmation/stage5c2d_finals.csv",
    "results/stage5c2d_lite/confirmation/stage5c2d_seed_registry.csv",
    "output/stage5c2f/haxs_stage5c2f_clean_source.zip",
    "output/stage5c2f/haxs_stage5c2f_results.zip",
    "output/stage5c2f/HAXS_Stage5C2F_Srinjoy_Submission_20260714.zip",
    # Retained full-suite tests execute predecessor compatibility checks from
    # the clean protocol root.  These immutable artifacts therefore belong to
    # the candidate-bound closure rather than being optional packaging extras.
    "output/stage5c2gR32/sanity_calibration/calibration_decision.json",
    "output/stage5c2gR32A1/haxs-0.8.4-py3-none-any.whl",
]


def runtime_paths(root: Path = ROOT) -> list[Path]:
    paths: list[Path] = []
    for base in ["configs", "scripts", "scripts_patch", "src", "tests", "docs"]:
        for path in (root / base).rglob("*"):
            if (
                path.is_file() and not path.is_symlink()
                and "__pycache__" not in path.parts and ".pytest_cache" not in path.parts
                and path.suffix.lower() in TEXT_SUFFIXES
            ):
                paths.append(path)
    paths.extend(root / relative for relative in ROOT_CONTRACTS)
    if any(not path.is_file() or path.is_symlink() for path in paths):
        raise RuntimeError("required runtime input is missing or unsafe")
    return sorted(set(paths))


def closure_paths(root: Path = ROOT) -> list[Path]:
    paths = [root / relative for relative in CUSTODY_PATHS]
    if any(not path.is_file() or path.is_symlink() for path in paths):
        raise RuntimeError("required custody input is missing or unsafe")
    return paths


def bound(path: Path) -> dict:
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256_file(path)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fail-closed", action="store_true", required=True)
    parser.add_argument("--out", type=Path, default=ROOT / "results/stage5c2gR32A2/protocol/CANDIDATE.json")
    args = parser.parse_args()
    if args.out.exists() or args.out.is_symlink():
        raise RuntimeError("refusing to overwrite R3.2A.2 candidate")
    wheel = ROOT / "output/stage5c2gR32A2/haxs-0.8.5-py3-none-any.whl"
    environment = ROOT / "results/stage5c2gR32A2/environment.json"
    dependency_lock = ROOT / "requirements-stage5c2gR3.lock"
    wheelhouse_manifest = ROOT / "ci/frozen/stage5c2gR32A2/WHEELHOUSE_MANIFEST_SHA256.txt"
    contracts = {
        "receipt_template": ROOT / "configs/stage5c2gR32A2/structured_receipt_template.json",
        "finalizer": ROOT / "scripts/finalize_stage5c2gR32A2_authorization.py",
        "comparator": ROOT / "scripts/compare_stage5c2gR32A2_g0_hosts.py",
        "root_verifier": ROOT / "scripts/verify_stage5c2gR32A2_root.py",
        "environment_verifier": ROOT / "scripts/verify_stage5c2gR32A2_environment.py",
        "launcher": ROOT / "scripts/launch_stage5c2gR32A2_G1_isolated.py",
        "runner": ROOT / "scripts/run_stage5c2gR32A2_G1.py",
        "g1_config": ROOT / "configs/stage5c2gR32A/g1_deterministic.yaml",
        "g1_plan": ROOT / "output/stage5c2gR32A/g1_preflight/quadrature_node_registry.csv",
        "unit_registry": ROOT / "output/stage5c2gR32A/g1_preflight/unit_registry.csv",
        "test_ledger": ROOT / "results/stage5c2gR32A2/protocol/NAMED_TEST_LEDGER.json",
        "adversarial_outcomes": ROOT / "results/stage5c2gR32A2/adversarial/OUTCOMES.json",
        "root_manifest": ROOT / "results/stage5c2gR32A2/protocol/ROOT_MANIFEST.json",
        "supersession_ledger": ROOT / "results/stage5c2gR32A2/protocol/SUPERSESSION.json",
    }
    required = [wheel, environment, dependency_lock, wheelhouse_manifest, *contracts.values()]
    if any(not path.is_file() or path.is_symlink() for path in required):
        raise RuntimeError("R3.2A.2 candidate input is missing or unsafe")
    runtime = {path.relative_to(ROOT).as_posix(): sha256_file(path) for path in runtime_paths()}
    closure = {path.relative_to(ROOT).as_posix(): sha256_file(path) for path in closure_paths()}
    payload = {
        "schema_version": "haxs.stage5c2gR32A2.candidate.v1",
        "stage": "stage5c2gR32A2",
        "predecessor_candidate_sha256": "f0f2a2e6deadc3d4ca4a7c9eab8064ff43d9502a26e3708c4773626f7d4ba711",
        "predecessor_disposition": "SUPERSEDED_NON_EXECUTABLE_NO_RECEIPT",
        "runtime_files": runtime,
        "runtime_tree_sha256": sha256_payload(runtime),
        "root_closure_files": closure,
        "root_closure_sha256": sha256_payload(closure),
        "wheel": bound(wheel),
        "environment": bound(environment),
        "dependency_lock": bound(dependency_lock),
        "wheelhouse_manifest": bound(wheelhouse_manifest),
        "authorization_contract": {name: bound(path) for name, path in contracts.items()},
        "scope": {
            "scientific_G1_design": "UNCHANGED_FROM_R3_2A_1",
            "g0_authorization": "SELF_RECOMPUTED_FROM_COMPLETE_PRIMARY_EVIDENCE",
            "root_policy": "WHOLE_ROOT_DENY_BY_DEFAULT_BYTECODE_CLOSED_V2",
            "attempt_order": "SETUP_PREFLIGHT_THEN_EXCLUSIVE_SCIENTIFIC_RESERVATION",
        },
        "execution_permissions": {
            "G1": "BLOCKED_PENDING_NEW_SUPERVISORY_REVIEW_AND_RECEIPT",
            "G2": "BLOCKED", "G3": "BLOCKED", "G4": "BLOCKED",
            "STAGE5C3": "BLOCKED", "STAGE5D": "BLOCKED",
            "MANUSCRIPT_RESULT_CLAIMS": "BLOCKED", "EXACT_MOBILE_HOLE_CLAIMS": "BLOCKED",
            "PUBLIC_RELEASE": "BLOCKED",
        },
    }
    payload["candidate_sha256"] = sha256_payload(payload)
    atomic_write_json(args.out, payload)
    print(json.dumps({
        "status": "AWAITING_REPLACEMENT_TWO_PHYSICAL_HOST_G0",
        "candidate_sha256": payload["candidate_sha256"],
        "runtime_files": len(runtime), "root_closure_files": len(closure),
        "wheel_sha256": payload["wheel"]["sha256"],
        "scientific_execution_performed": False, "G1_authorized": False,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
