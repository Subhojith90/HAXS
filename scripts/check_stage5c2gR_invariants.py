#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2gR_common import load_yaml, physical_random_unit, planned_fixed_count_registry, scientific_paths


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--planned", action="store_true")
    parser.add_argument("--out", default="results/stage5c2gR/invariants")
    args = parser.parse_args()
    benchmark = load_yaml("configs/stage5c2gR/exact_mobile_benchmark.yaml")["stage5c2gR_exact_benchmark"]
    fixed_raw = load_yaml("configs/stage5c2gR/fixed_count.yaml")
    fixed = fixed_raw["stage5c2gR_fixed_count"]
    protocol = load_yaml("configs/stage5c2gR/protocol.yaml")["stage5c2gR_protocol"]
    rows = []

    def add(check: str, passed: bool, detail: str) -> None:
        rows.append({"check": check, "passed": bool(passed), "detail": detail})

    planned = pd.concat([planned_fixed_count_registry(fixed_raw, count) for count in fixed["fixed_hole_counts"]], ignore_index=True)
    expected = 3 * 16 * 6 * 4 * 2
    add("fixed_count_planned_rows", len(planned) == expected, f"actual={len(planned)} expected={expected}")
    for column, keys in [("occupancy_seed", ["hole_count", "occupancy_idx"]), ("hole_path_seed", ["hole_count", "occupancy_idx", "path_idx"]), ("phase_batch_seed", ["hole_count", "occupancy_idx", "path_idx", "phase_idx"])]:
        units = planned[[*keys, column]].drop_duplicates()
        add(f"{column}_is_physical_and_label_independent", units.groupby(keys)[column].nunique().eq(1).all(), f"units={len(units)}")
    domains = {column: set(planned[column].astype(int)) for column in ["occupancy_seed", "hole_path_seed", "phase_batch_seed"]}
    add("fixed_seed_domains_disjoint", not ((domains["occupancy_seed"] & domains["hole_path_seed"]) | (domains["occupancy_seed"] & domains["phase_batch_seed"]) | (domains["hole_path_seed"] & domains["phase_batch_seed"])), "three domains")

    exact_units = []
    hierarchy = benchmark["hierarchy"]
    for split in ["calibration", "validation"]:
        for case in benchmark[f"{split}_cases"]:
            labels = case.get("labels", benchmark["labels"])
            for occupancy_idx in range(int(hierarchy["occupancy_replicates"])):
                for path_idx in range(int(hierarchy["paths_per_occupancy"])):
                    for phase_idx in range(int(hierarchy["phase_batches_per_path"])):
                        unit = physical_random_unit(benchmark["namespace_uuid"], split, case["id"], occupancy_idx, path_idx, phase_idx)
                        for label in labels: exact_units.append({"split": split, "case_id": case["id"], "occupancy_idx": occupancy_idx, "path_idx": path_idx, "phase_idx": phase_idx, "label": label, **unit})
    exact_frame = pd.DataFrame(exact_units)
    physical_keys = ["split", "case_id", "occupancy_idx", "path_idx", "phase_idx"]
    for column in ["occupancy_seed", "hole_path_seed", "phase_batch_seed", "occupancy_realization_id", "hole_path_realization_id", "phase_batch_realization_id", "exact_initial_state_id"]:
        add(f"exact_{column}_label_independent", exact_frame.groupby(physical_keys)[column].nunique().eq(1).all(), f"physical_units={exact_frame.groupby(physical_keys).ngroups}")
    calibration_ids = {case["id"] for case in benchmark["calibration_cases"]} | {case["id"] for case in benchmark["transport_calibration_cases"]}
    validation_ids = {case["id"] for case in benchmark["validation_cases"]}
    add("calibration_validation_ids_disjoint", calibration_ids.isdisjoint(validation_ids), f"calibration={len(calibration_ids)} validation={len(validation_ids)}")
    add("multiple_path_and_phase_units", int(hierarchy["paths_per_occupancy"]) > 1 and int(hierarchy["phase_batches_per_path"]) > 1, str(hierarchy))
    add("practical_effect_threshold_positive", float(fixed["inference"]["smallest_effect_of_scientific_interest_db"]) > 0.0, str(fixed["inference"]))
    add("simultaneous_inference_declared", "simultaneous" in fixed["inference"]["simultaneous_method"] or "maximum" in fixed["inference"]["simultaneous_method"], fixed["inference"]["simultaneous_method"])
    add("topology_scope_honest", fixed["topology_scope"]["confirmatory"] is False, fixed["claim_scope"])
    covered = {str(path.relative_to(ROOT)) for path in scientific_paths(ROOT)}
    required = {"src/haxs/models/mobile_holes.py", "src/haxs/models/spin_density.py", "src/haxs/lattice/occupancy.py", "src/haxs/observables/squeezing.py", "src/haxs/utils/rng.py", "src/haxs/validation/random_effects.py", "src/haxs/io/result_store.py"}
    add("scientific_dependency_closure_contains_audit_targets", required <= covered, ";".join(sorted(required - covered)))
    add("old_candidate_explicitly_forbidden", "current_stage5c2g_candidate_finalization_or_execution" in protocol["forbidden_actions"], "old candidate rejected")

    failed = [row["check"] for row in rows if not row["passed"]]
    summary = {"stage": "stage5c2gR_planned_invariant_gate", "status": "PASS" if not failed else "FAIL", "failed_checks": failed}
    output = ROOT / args.out; output.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output / "stage5c2gR_invariants.csv", index=False)
    (output / "stage5c2gR_invariant_gate.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    if failed: raise SystemExit(1)


if __name__ == "__main__":
    main()

