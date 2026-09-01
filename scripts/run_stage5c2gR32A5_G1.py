#!/usr/bin/env python
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from stage5c2gR32A5_common import atomic_write_json, load_candidate, sha256_file, sha256_payload


def main() -> None:
    if not sys.flags.isolated or sys.flags.no_user_site != 1 or len(sys.argv) != 1:
        raise SystemExit("official A5 G1 runner requires isolated no-override execution")
    attestation_path = Path(os.environ.get("HAXS_R32A5_LAUNCH_ATTESTATION", ""))
    if not attestation_path.is_file() or attestation_path.is_symlink():
        raise SystemExit("official A5 launch attestation is missing or unsafe")
    attestation = json.loads(attestation_path.read_text(encoding="utf-8"))
    required = {
        "schema_version", "candidate_sha256", "receipt_id", "wheel_sha256",
        "runner_sha256", "g1_config_sha256", "installed_target", "output_path",
        "attestation_sha256",
    }
    canonical = {key: value for key, value in attestation.items() if key != "attestation_sha256"}
    if (
        set(attestation) != required
        or attestation["schema_version"] != "haxs.stage5c2gR32A5.G1-launch.v1"
        or attestation["attestation_sha256"] != sha256_payload(canonical)
    ):
        raise SystemExit("official A5 launch attestation schema or identity failed")
    candidate = load_candidate()
    contracts = candidate["authorization_contract"]
    if (
        attestation["candidate_sha256"] != candidate["candidate_sha256"]
        or attestation["wheel_sha256"] != candidate["wheel"]["sha256"]
        or attestation["runner_sha256"] != contracts["runner"]["sha256"]
        or attestation["g1_config_sha256"] != contracts["g1_config"]["sha256"]
        or sha256_file(Path(__file__)) != contracts["runner"]["sha256"]
    ):
        raise SystemExit("official A5 launch attestation differs from candidate contracts")
    installed = Path(attestation["installed_target"]).resolve(strict=True)
    output = Path(attestation["output_path"]).absolute()
    if output.exists() or output.is_symlink() or output.is_relative_to(ROOT.resolve()):
        raise SystemExit("official A5 scientific output root is not fresh and external")
    sys.path.insert(0, str(installed))
    import haxs
    if not Path(haxs.__file__).resolve().is_relative_to(installed):
        raise SystemExit("HAXS import did not originate from the candidate-bound wheel")
    from run_stage5c2gR32A_phase_quadrature import run

    config = ROOT / contracts["g1_config"]["path"]
    result = run(config, output)
    if result.get("status") != "PASS":
        raise RuntimeError("official deterministic A5 G1 predicate failed")
    runtime = {
        "schema_version": "haxs.stage5c2gR32A5.G1-runtime.v1",
        "candidate_sha256": candidate["candidate_sha256"],
        "receipt_id": attestation["receipt_id"],
        "wheel_sha256": candidate["wheel"]["sha256"],
        "runner_sha256": sha256_file(Path(__file__)),
        "isolated": True,
        "haxs_from_installed_wheel": True,
        "installed_haxs_tree": str(Path(haxs.__file__).resolve().relative_to(installed)),
    }
    runtime["runtime_sha256"] = sha256_payload(runtime)
    atomic_write_json(output / "G1_RUNTIME_ATTESTATION.json", runtime)
    official = {
        "schema_version": "haxs.stage5c2gR32A5.official-G1.v1",
        "gate": "G1", "status": "PASS",
        "candidate_sha256": candidate["candidate_sha256"],
        "receipt_id": attestation["receipt_id"],
        "maximum_difference": result["maximum_difference"],
        "absolute_sanity_passed": result["absolute_sanity_passed"],
        "analytic_t0_passed": result["analytic_t0_passed"],
        "dt_convergence_passed": result["dt_convergence_passed"],
        "independent_semantics_agree": result["independent_semantics_agree"],
        "downstream_permission": "NONE_RETURN_FOR_SUPERVISORY_REVIEW",
    }
    official["decision_sha256"] = sha256_payload(official)
    atomic_write_json(output / "OFFICIAL_G1_VERIFICATION.json", official)
    print(json.dumps(official, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
