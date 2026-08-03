#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))
from stage5c2gR32A1_authorization import (
    ROOT,
    atomic_write_json,
    sha256_file,
    sha256_payload,
)

TEXT_SUFFIXES = {
    ".py",
    ".yaml",
    ".yml",
    ".json",
    ".md",
    ".sh",
    ".txt",
    ".csv",
    ".toml",
    ".lock",
}
ROOT_CONTRACTS = [
    "README.md",
    "STAGE3_COMMANDS.sh",
    "STAGE3A_COMMANDS.sh",
    "STAGE5C2GR3_COMMANDS.sh",
    "STAGE5C2GR32_COMMANDS.sh",
    "pyproject.toml",
    "requirements-stage5c2gR2.lock",
    "requirements-stage5c2gR3.in",
    "requirements-stage5c2gR3.lock",
]
CUSTODY_PATHS = [
    "results/stage5c2d_lite/confirmation/stage5c2d_block_manifest.json",
    "results/stage5c2d_lite/confirmation/stage5c2d_curves_all.csv",
    "results/stage5c2d_lite/confirmation/stage5c2d_finals.csv",
    "results/stage5c2d_lite/confirmation/stage5c2d_seed_registry.csv",
    "output/stage5c2f/haxs_stage5c2f_clean_source.zip",
    "output/stage5c2f/haxs_stage5c2f_results.zip",
    "output/stage5c2f/HAXS_Stage5C2F_Srinjoy_Submission_20260714.zip",
]
RETIRED_EXECUTABLES = {
    "scripts/finalize_stage5c2gR32_authorization.py",
    "scripts/launch_stage5c2gR32_G1_isolated.py",
}


def runtime_paths(root: Path = ROOT) -> list[Path]:
    paths: list[Path] = []
    for base in ["configs", "scripts", "scripts_patch", "src", "tests", "docs"]:
        directory = root / base
        for path in directory.rglob("*"):
            if (
                path.is_file()
                and not path.is_symlink()
                and "__pycache__" not in path.parts
                and ".pytest_cache" not in path.parts
                and path.suffix.lower() in TEXT_SUFFIXES
                and path.relative_to(root).as_posix() not in RETIRED_EXECUTABLES
            ):
                paths.append(path)
    paths.extend(root / relative for relative in ROOT_CONTRACTS)
    missing = [path.as_posix() for path in paths if not path.is_file()]
    if missing:
        raise RuntimeError(f"required runtime root file missing: {missing}")
    if any(path.is_symlink() for path in paths):
        raise RuntimeError("candidate runtime contains a symlink")
    return sorted(set(paths))


def closure_paths(root: Path = ROOT) -> list[Path]:
    paths = [root / relative for relative in CUSTODY_PATHS]
    missing = [path.as_posix() for path in paths if not path.is_file()]
    if missing:
        raise RuntimeError(f"self-contained custody file missing: {missing}")
    if any(path.is_symlink() for path in paths):
        raise RuntimeError("self-contained custody contains a symlink")
    return paths


def _bound(path: Path) -> dict:
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256_file(path)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fail-closed", action="store_true", required=True)
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "results/stage5c2gR32A1/protocol/CANDIDATE.json",
    )
    args = parser.parse_args()
    if args.out.exists() or args.out.is_symlink():
        raise RuntimeError("refusing to overwrite an R3.2A.1 candidate")

    gates = {
        "deterministic_G1": ROOT
        / "output/stage5c2gR32A/g1_preflight/verification.json",
        "stochastic_development": ROOT
        / "output/stage5c2gR32A/s03_development/decision.json",
        "stochastic_validation": ROOT
        / "output/stage5c2gR32A/s03_validation/decision.json",
    }
    gate_records = {}
    for name, path in gates.items():
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("status") != "PASS":
            raise RuntimeError(f"{name} has not passed")
        gate_records[name] = _bound(path)

    wheel = ROOT / "output/stage5c2gR32A1/haxs-0.8.4-py3-none-any.whl"
    environment = ROOT / "results/stage5c2gR32A1/environment.json"
    contracts = {
        "receipt_template": ROOT
        / "configs/stage5c2gR32A1/structured_receipt_template.json",
        "finalizer": ROOT / "scripts/finalize_stage5c2gR32A1_authorization.py",
        "launcher": ROOT / "scripts/launch_stage5c2gR32A1_G1_isolated.py",
        "runner": ROOT / "scripts/run_stage5c2gR32A1_G1.py",
        "g1_config": ROOT / "configs/stage5c2gR32A/g1_deterministic.yaml",
        "g1_plan": ROOT
        / "output/stage5c2gR32A/g1_preflight/quadrature_node_registry.csv",
        "unit_registry": ROOT
        / "output/stage5c2gR32A/g1_preflight/unit_registry.csv",
        "test_ledger": ROOT
        / "results/stage5c2gR32A1/protocol/NAMED_TEST_LEDGER.json",
        "root_manifest": ROOT
        / "results/stage5c2gR32A1/protocol/ROOT_MANIFEST.json",
    }
    required = [wheel, environment, *contracts.values()]
    if any(not path.is_file() or path.is_symlink() for path in required):
        missing = [path.as_posix() for path in required if not path.is_file()]
        raise RuntimeError(f"R3.2A.1 candidate input missing or unsafe: {missing}")

    runtime = {
        path.relative_to(ROOT).as_posix(): sha256_file(path)
        for path in runtime_paths()
    }
    closure = {
        path.relative_to(ROOT).as_posix(): sha256_file(path)
        for path in closure_paths()
    }
    payload = {
        "schema_version": "haxs.stage5c2gR32A1.candidate.v1",
        "stage": "stage5c2gR32A1",
        "predecessor_candidate_sha256": "1950c01dfd46f4c381e2d333dbd2c3bce1969b65140689961662c287dd54c165",
        "predecessor_disposition": "SUPERSEDED_NON_EXECUTABLE_NO_RECEIPT",
        "runtime_files": runtime,
        "runtime_tree_sha256": sha256_payload(runtime),
        "root_closure_files": closure,
        "root_closure_sha256": sha256_payload(closure),
        "wheel": _bound(wheel),
        "environment": _bound(environment),
        "gates": gate_records,
        "authorization_contract": {
            name: _bound(path) for name, path in contracts.items()
        },
        "scope": {
            "binding_G1_certificate": "deterministic_four_unit_quadrature",
            "stochastic_calibration_role": "non_authorising_scale_extension",
            "root_policy": "exact_self_contained_deny_by_default_v1",
        },
        "execution_permissions": {
            "G1": "BLOCKED_PENDING_REPLACEMENT_TWO_PHYSICAL_HOST_G0_SUPERVISORY_ACCEPTANCE_AND_NEW_RECEIPT",
            "G2": "BLOCKED",
            "G3": "BLOCKED",
            "G4": "BLOCKED",
            "STAGE5C3": "BLOCKED",
            "STAGE5D": "BLOCKED",
            "MANUSCRIPT_RESULT_CLAIMS": "BLOCKED",
            "EXACT_MOBILE_HOLE_CLAIMS": "BLOCKED",
            "PUBLIC_RELEASE": "BLOCKED",
        },
    }
    payload["candidate_sha256"] = sha256_payload(payload)
    atomic_write_json(args.out, payload)
    print(
        json.dumps(
            {
                "status": "AWAITING_REPLACEMENT_TWO_PHYSICAL_HOST_G0",
                "candidate_sha256": payload["candidate_sha256"],
                "runtime_files": len(runtime),
                "root_closure_files": len(closure),
                "wheel_sha256": payload["wheel"]["sha256"],
                "scientific_execution_performed": False,
                "G1_authorized": False,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
