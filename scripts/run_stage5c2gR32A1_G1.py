#!/usr/bin/env python
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if not sys.flags.isolated or sys.flags.no_user_site != 1:
    raise SystemExit("official R3.2A.1 G1 runner requires isolated mode (-I)")
if len(sys.argv) != 1:
    raise SystemExit("official R3.2A.1 G1 runner accepts no overrides")

attestation_path = Path(os.environ.get("HAXS_R32A1_LAUNCH_ATTESTATION", ""))
if not attestation_path.is_file() or attestation_path.is_symlink():
    raise SystemExit("official R3.2A.1 launch attestation is missing or unsafe")
attestation = json.loads(attestation_path.read_text(encoding="utf-8"))
expected_keys = {
    "schema_version",
    "candidate_sha256",
    "lock_sha256",
    "wheel_sha256",
    "installed_target",
    "execution_root",
    "output_path",
    "nonce",
    "launcher_sha256",
}
if (
    set(attestation) != expected_keys
    or attestation.get("schema_version")
    != "haxs.stage5c2gR32A1.G1-launch.v1"
    or Path(attestation["execution_root"]).resolve() != ROOT.resolve()
):
    raise SystemExit("official R3.2A.1 launch attestation schema or root failed")

installed = Path(attestation["installed_target"]).resolve()
output = Path(attestation["output_path"]).resolve()
if not output.is_relative_to(
    ROOT
    / "results/stage5c2gR32A1/artifacts"
    / attestation["candidate_sha256"]
    / "G1"
):
    raise SystemExit("official R3.2A.1 artifact root is not canonical")
os.environ["HAXS_R32A1_INSTALLED_TARGET"] = str(installed)
sys.path.insert(0, str(installed))
sys.path.insert(1, str(ROOT / "scripts"))

import haxs

if not Path(haxs.__file__).resolve().is_relative_to(installed):
    raise SystemExit("HAXS import did not originate from the candidate-bound wheel")

from run_stage5c2gR32A_phase_quadrature import run
from stage5c2gR32A1_authorization import (
    atomic_write_json,
    load_candidate,
    load_lock,
    sha256_file,
    sha256_payload,
)


def main() -> None:
    candidate = load_candidate()
    lock = load_lock(candidate)
    if (
        attestation["candidate_sha256"] != candidate["candidate_sha256"]
        or attestation["lock_sha256"] != lock["lock_sha256"]
        or attestation["wheel_sha256"] != candidate["wheel"]["sha256"]
        or attestation["launcher_sha256"]
        != candidate["authorization_contract"]["launcher"]["sha256"]
    ):
        raise RuntimeError("launch attestation differs from the current lock or candidate")
    config = ROOT / candidate["authorization_contract"]["g1_config"]["path"]
    result = run(config, output)
    if result.get("status") != "PASS":
        raise RuntimeError("official deterministic G1 predicate failed")
    runtime = {
        "schema_version": "haxs.stage5c2gR32A1.G1-runtime.v1",
        "candidate_sha256": candidate["candidate_sha256"],
        "wheel_sha256": candidate["wheel"]["sha256"],
        "lock_sha256": lock["lock_sha256"],
        "isolated": bool(sys.flags.isolated),
        "haxs_from_installed_wheel": Path(haxs.__file__).resolve().is_relative_to(
            installed
        ),
        "haxs_origin": str(Path(haxs.__file__).resolve()),
        "runner_sha256": sha256_file(Path(__file__)),
    }
    atomic_write_json(output / "G1_RUNTIME_ATTESTATION.json", runtime)
    official = {
        "schema_version": "haxs.stage5c2gR32A1.official-G1.v1",
        "gate": "G1",
        "status": "PASS",
        "candidate_sha256": candidate["candidate_sha256"],
        "lock_sha256": lock["lock_sha256"],
        "receipt_id": lock["receipt_id"],
        "binding_scope": "deterministic_four_unit_quadrature",
        "source_verification_sha256": sha256_file(output / "verification.json"),
        "source_manifest_sha256": sha256_file(output / "MANIFEST.json"),
        "maximum_difference": result["maximum_difference"],
        "absolute_sanity_passed": result["absolute_sanity_passed"],
        "analytic_t0_passed": result["analytic_t0_passed"],
        "dt_convergence_passed": result["dt_convergence_passed"],
        "independent_semantics_agree": result["independent_semantics_agree"],
        "downstream_permission": "NONE_RETURN_FOR_SUPERVISORY_REVIEW",
    }
    official["decision_sha256"] = sha256_payload(official)
    atomic_write_json(output / "OFFICIAL_G1_VERIFICATION.json", official)
    file_hashes = {
        path.relative_to(output).as_posix(): sha256_file(path)
        for path in sorted(output.rglob("*"))
        if path.is_file() and path.name != "OFFICIAL_G1_MANIFEST.json"
    }
    official_manifest = {
        "schema_version": "haxs.stage5c2gR32A1.official-G1-manifest.v1",
        "candidate_sha256": candidate["candidate_sha256"],
        "files": file_hashes,
    }
    official_manifest["manifest_sha256"] = sha256_payload(official_manifest)
    atomic_write_json(
        output / "OFFICIAL_G1_MANIFEST.json", official_manifest
    )
    print(json.dumps(official, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
