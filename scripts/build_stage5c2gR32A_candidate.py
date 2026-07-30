#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2gR32_common import atomic_write_json, sha256_file, sha256_payload
from stage5c2gR32A_common import predecessor_identity


def runtime_paths() -> list[Path]:
    paths: list[Path] = []
    for base in ["configs", "scripts", "scripts_patch", "src", "tests", "docs"]:
        directory = ROOT / base
        for path in directory.rglob("*"):
            if (
                path.is_file()
                and not path.is_symlink()
                and "__pycache__" not in path.parts
                and ".pytest_cache" not in path.parts
                and path.suffix.lower() in {".py", ".yaml", ".yml", ".json", ".md", ".sh", ".txt", ".csv", ".toml"}
            ):
                paths.append(path)
    for name in ["pyproject.toml", "requirements-stage5c2gR3.lock", "requirements-stage5c2gR3.in", "README.md"]:
        path = ROOT / name
        if path.is_file():
            paths.append(path)
    if any(path.is_symlink() for path in paths):
        raise RuntimeError("candidate runtime contains a symlink")
    return sorted(set(paths))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fail-closed", action="store_true", required=True)
    args = parser.parse_args()
    gates = {
        "deterministic_G1": ROOT / "output/stage5c2gR32A/g1_preflight/verification.json",
        "stochastic_development": ROOT / "output/stage5c2gR32A/s03_development/decision.json",
        "stochastic_validation": ROOT / "output/stage5c2gR32A/s03_validation/decision.json",
    }
    gate_records = {}
    for name, path in gates.items():
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("status") != "PASS":
            raise RuntimeError(f"{name} has not passed")
        gate_records[name] = {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256_file(path)}
    wheel = ROOT / "output/stage5c2gR32A/haxs-0.8.3-py3-none-any.whl"
    environment = ROOT / "results/stage5c2gR32A/environment.json"
    if not wheel.is_file() or not environment.is_file():
        raise RuntimeError("immutable wheel and environment attestation are required")
    runtime = {path.relative_to(ROOT).as_posix(): sha256_file(path) for path in runtime_paths()}
    payload = {
        "schema_version": "haxs.stage5c2gR32A.candidate.v1",
        "stage": "stage5c2gR32A",
        "predecessor_candidate_sha256": "91344d090d9f3387781c4e53bbbe4a5c9b359eaa82f47373b2d4f55cfcf2a2a3",
        "predecessor_terminal_status": "FAILED",
        "predecessor_evidence": predecessor_identity(),
        "runtime_files": runtime,
        "runtime_tree_sha256": sha256_payload(runtime),
        "wheel": {"path": wheel.relative_to(ROOT).as_posix(), "sha256": sha256_file(wheel)},
        "environment": {"path": environment.relative_to(ROOT).as_posix(), "sha256": sha256_file(environment)},
        "gates": gate_records,
        "scope": {
            "binding_G1_certificate": "deterministic_four_unit_quadrature",
            "stochastic_calibration_role": "non_authorising_scale_extension",
        },
        "execution_permissions": {
            "G1": "BLOCKED_PENDING_TWO_PHYSICAL_HOST_G0_SUPERVISORY_ACCEPTANCE_AND_NEW_RECEIPT",
            "G2": "BLOCKED", "G3": "BLOCKED", "G4": "BLOCKED",
            "STAGE5C3": "BLOCKED", "STAGE5D": "BLOCKED",
            "MANUSCRIPT_RESULT_CLAIMS": "BLOCKED",
            "EXACT_MOBILE_HOLE_CLAIMS": "BLOCKED", "PUBLIC_RELEASE": "BLOCKED",
        },
    }
    payload["candidate_sha256"] = sha256_payload(payload)
    destination = ROOT / "results/stage5c2gR32A/protocol/CANDIDATE.json"
    if destination.exists():
        raise RuntimeError("refusing to overwrite an existing R3.2A candidate")
    atomic_write_json(destination, payload)
    print(json.dumps({
        "status": "AWAITING_TWO_PHYSICAL_HOST_G0",
        "candidate_sha256": payload["candidate_sha256"],
        "runtime_files": len(runtime),
        "wheel_sha256": payload["wheel"]["sha256"],
        "scientific_execution_performed": False,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
