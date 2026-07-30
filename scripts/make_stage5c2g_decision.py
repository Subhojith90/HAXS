#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", default="results/stage5c2g")
    args = parser.parse_args()
    root = ROOT / args.results
    fixed = json.loads((root / "fixed_count_analysis/stage5c2g_fixed_count_gate.json").read_text(encoding="utf-8"))
    validity = json.loads((root / "validity_analysis/stage5c2g_validity_gate.json").read_text(encoding="utf-8"))
    fixed_pass, validity_pass = bool(fixed["passed"]), bool(validity["passed"])
    if fixed_pass and validity_pass:
        route = "request_approval_for_small_stage5c3_untouched_geometry_preflight"
        interpretation = "fixed-count confounding and small-system validity gates passed"
    elif fixed_pass and not validity_pass:
        route = "stop_surrogate_physics_claims_and_rebuild_or_reframe_as_validation_failure"
        interpretation = "fixed-count signal survives but current surrogate fails controlled validity"
    elif validity_pass and not fixed_pass:
        route = "pivot_to_conditional_hole_severity_topology_threshold_map"
        interpretation = "surrogate validity passes but target effect is not generic across controlled hole strata"
    else:
        route = "stop_stage5c_mechanism_expansion"
        interpretation = "both fixed-count and controlled-validity gates failed"
    payload = {
        "stage": "stage5c2g_source_generated_decision",
        "fixed_count_gate_passed": fixed_pass,
        "small_system_validity_gate_passed": validity_pass,
        "both_gates_passed": bool(fixed_pass and validity_pass),
        "stage5c3_untouched_geometry_preflight_may_be_requested": bool(fixed_pass and validity_pass),
        "stage5c3_production_allowed": False,
        "stage5d_allowed": False,
        "manuscript_result_claims_allowed": False,
        "public_release_allowed": False,
        "route": route,
        "interpretation": interpretation,
    }
    output = root / "decision"
    output.mkdir(parents=True, exist_ok=True)
    (output / "stage5c2g_decision.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()

