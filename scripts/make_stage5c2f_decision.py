#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--analysis", default="results/stage5c2f/analysis")
    ap.add_argument("--hierarchy-gate", default="results/stage5c2f/preflight/stage5c2f_hierarchy_gate.json")
    args = ap.parse_args()
    analysis = ROOT / args.analysis
    hierarchy = json.loads((ROOT / args.hierarchy_gate).read_text(encoding="utf-8"))
    gates = pd.read_csv(analysis / "stage5c2f_gate_table.csv")
    primary = gates[gates.block == "primary"].iloc[0]
    confirmation = gates[gates.block == "confirmation"].iloc[0]
    required = ["fixed_time_mean_pass", "fixed_time_ci_pass", "absolute_mc_se_pass", "occupancy_negative_fraction_pass", "local_window_all_negative", "equivalence_pass"]
    reasons = []
    if hierarchy["status"] != "PASS":
        reasons.append("hierarchy_or_seed_namespace_gate_failed")
    for name in required:
        if not bool(primary[name]):
            reasons.append(f"primary_{name}_failed")
    if not bool(confirmation["local_window_all_negative"]):
        reasons.append("frozen_confirmation_local_window_failed")
    passed = not reasons
    payload = {
        "stage": "stage5c2f_source_generated_decision",
        "decision": "PASS" if passed else "FAIL",
        "target_shape_primary_relock_passed": passed,
        "stage5c3_data_production_allowed": False,
        "stage5d_allowed": False,
        "public_release_allowed": False,
        "next_action": "request_supervisor_review" if passed else "stop_and_submit_failed_gate",
        "reasons": reasons or ["all_preregistered_stage5c2f_gates_passed"],
    }
    path = analysis / "stage5c2f_decision.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
