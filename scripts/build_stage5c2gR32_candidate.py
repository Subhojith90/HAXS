#!/usr/bin/env python
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2gR32_common import (
    atomic_write_json,
    file_manifest,
    sha256_file,
    sha256_payload,
)

REQUIRED_GATE_FILES = {
    "S01": ROOT / "results/stage5c2gR32/S01/verification.json",
    "S02": ROOT / "output/stage5c2gR32/g1_preflight/verification.json",
    "S03": ROOT / "output/stage5c2gR32/sanity_calibration/calibration_decision.json",
}
REQUIRED_GATE_MANIFESTS = {
    "S01": ROOT / "results/stage5c2gR32/S01/MANIFEST.json",
    "S02": ROOT / "output/stage5c2gR32/g1_preflight/MANIFEST.json",
    "S03": ROOT / "output/stage5c2gR32/sanity_calibration/MANIFEST.json",
}
REQUIRED_GATE_SUPPLEMENTAL = {
    "S01": [
        ROOT / "results/stage5c2gR32/S01/supersession_ledger.json",
        ROOT / "results/stage5c2gR32/S01/regenerated_semantic_decision.json",
        ROOT / "results/stage5c2gR32/S01/manifest_check.csv",
    ]
}


def runtime_paths() -> list[Path]:
    paths = []
    for base in [
        ROOT / "configs",
        ROOT / "scripts",
        ROOT / "scripts_patch",
        ROOT / "src/haxs",
        ROOT / "tests",
        ROOT / "docs/stage5c2gR32",
    ]:
        paths.extend(
            path
            for path in base.rglob("*")
            if path.is_file()
            and "__pycache__" not in path.parts
            and path.suffix.lower()
            in {".py", ".yaml", ".yml", ".json", ".md", ".sh", ".txt", ".csv"}
        )
    paths.extend(
        [
            ROOT / "pyproject.toml",
            ROOT / "requirements-stage5c2gR3.lock",
            ROOT / "STAGE5C2GR32_COMMANDS.sh",
        ]
    )
    missing = [path for path in paths if not path.is_file()]
    if missing:
        raise RuntimeError(f"R3.2 runtime file set is incomplete: {missing}")
    if any(path.is_symlink() for path in paths):
        raise RuntimeError("R3.2 runtime file set contains a symlink")
    return sorted(set(paths))


def build() -> dict:
    gates = {}
    for name, path in REQUIRED_GATE_FILES.items():
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("status") != "PASS":
            raise RuntimeError(f"{name} has not passed; candidate creation is blocked")
        gates[name] = {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256_file(path)}
    for name, path in REQUIRED_GATE_MANIFESTS.items():
        gates[name]["manifest_path"] = path.relative_to(ROOT).as_posix()
        gates[name]["manifest_sha256"] = sha256_file(path)
    for name, paths in REQUIRED_GATE_SUPPLEMENTAL.items():
        gates[name]["supplemental"] = {
            path.relative_to(ROOT).as_posix(): sha256_file(path) for path in paths
        }

    wheel = ROOT / "output/stage5c2gR32/haxs-0.8.2-py3-none-any.whl"
    if not wheel.is_file() or wheel.is_symlink():
        raise RuntimeError(
            "build the non-editable haxs-0.8.2 wheel before candidate creation"
        )
    runtime = {
        path.relative_to(ROOT).as_posix(): sha256_file(path) for path in runtime_paths()
    }
    configs = {
        path.name: sha256_file(path)
        for path in sorted((ROOT / "configs/stage5c2gR32").iterdir())
        if path.is_file()
    }
    payload = {
        "schema_version": "haxs.stage5c2gR32.candidate.v1",
        "stage": "stage5c2gR32",
        "predecessor_candidate_sha256": "91344d090d9f3387781c4e53bbbe4a5c9b359eaa82f47373b2d4f55cfcf2a2a3",
        "predecessor_terminal_status": "FAILED",
        "predecessor_receipt_reusable": False,
        "runtime_files": runtime,
        "runtime_tree_sha256": sha256_payload(runtime),
        "config_hashes": configs,
        "pre_candidate_gates": gates,
        "wheel": {
            "path": wheel.relative_to(ROOT).as_posix(),
            "sha256": sha256_file(wheel),
        },
        "execution_permissions": {
            "G1": "BLOCKED_PENDING_TWO_HOST_G0_SUPERVISORY_ACCEPTANCE_AND_NEW_RECEIPT",
            "G2": "BLOCKED",
            "G3": "BLOCKED",
            "G4": "BLOCKED",
            "STAGE5C3": "BLOCKED",
            "STAGE5D": "BLOCKED",
            "PUBLIC_RELEASE": "BLOCKED",
        },
    }
    candidate_sha = sha256_payload(payload)
    candidate = {**payload, "candidate_sha256": candidate_sha}
    destination = ROOT / "results/stage5c2gR32/protocol/CANDIDATE.json"
    atomic_write_json(destination, candidate)
    return candidate


def main() -> None:
    if len(sys.argv) != 1:
        raise SystemExit("R3.2 candidate builder accepts no identity overrides")
    candidate = build()
    print(
        json.dumps(
            {
                "status": "AWAITING_TWO_HOST_G0_AND_SUPERVISORY_ACCEPTANCE",
                "candidate_sha256": candidate["candidate_sha256"],
                "runtime_tree_sha256": candidate["runtime_tree_sha256"],
                "runtime_files": len(candidate["runtime_files"]),
                "wheel_sha256": candidate["wheel"]["sha256"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
