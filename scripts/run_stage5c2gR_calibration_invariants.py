#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "scripts"))
from haxs.lattice.graphs import hypercubic_lattice
from haxs.lattice.occupancy import sample_fixed_count
from haxs.methods.constrained_spin_hole import run_constrained_curve
from haxs.methods.dtwa import run_dtwa
from stage5c2gR_common import assert_protocol_locked, load_yaml, physical_random_unit, sha256_payload


def holes_for(case: dict, occupancy_idx: int, seed: int, n_sites: int) -> list[int]:
    if occupancy_idx == 0: return [int(value) for value in case["holes"]]
    occupancy = sample_fixed_count(n_sites, len(case["holes"]), seed)
    return np.flatnonzero(~occupancy).astype(int).tolist()


def main() -> None:
    raise SystemExit("REJECTED LEGACY ROUTE: Stage 5C.2G-R G1 is disabled; use canonical Stage 5C.2G-R2 G1")
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/stage5c2gR/exact_mobile_benchmark.yaml")
    parser.add_argument("--protocol", default="configs/stage5c2gR/protocol.yaml")
    parser.add_argument("--out", default="results/stage5c2gR/calibration_invariants")
    args = parser.parse_args()
    lock = assert_protocol_locked(protocol_path=args.protocol)
    benchmark = load_yaml(args.config)["stage5c2gR_exact_benchmark"]; protocol = load_yaml(args.protocol)["stage5c2gR_protocol"]
    tolerance = float(protocol["calibration_gates"]["zero_coupling_max_abs_difference_db"])
    times = np.linspace(float(benchmark["times"]["start"]), float(benchmark["times"]["stop"]), int(benchmark["times"]["points"]))
    namespace = benchmark["namespace_uuid"]; hierarchy = benchmark["hierarchy"]; exact_config = benchmark["exact_model"]; surrogate = benchmark["surrogate"]
    limit_cases = [case for case in benchmark["calibration_cases"] if str(case["id"]).startswith("limit_")]
    rows = []
    for case in limit_cases:
        graph = hypercubic_lattice(tuple(case["shape"]), False); labels = case["labels"]; compared_label = [label for label in labels if label != "static_only"][0]
        for occupancy_idx in range(int(hierarchy["occupancy_replicates"])):
            base = physical_random_unit(namespace, "calibration_invariants", case["id"], occupancy_idx, 0, 0); holes = holes_for(case, occupancy_idx, base["occupancy_seed"], graph.n_sites)
            occupancy = np.ones(graph.n_sites, dtype=bool); occupancy[holes] = False
            for path_idx in range(int(hierarchy["paths_per_occupancy"])):
                for phase_idx in range(int(hierarchy["phase_batches_per_path"])):
                    unit = physical_random_unit(namespace, "calibration_invariants", case["id"], occupancy_idx, path_idx, phase_idx)
                    exact_curves = {}; surrogate_curves = {}
                    for label in labels:
                        hopping = 0.0
                        exact_lambda = 0.0
                        eta = 0.0
                        surrogate_lambda = 0.0
                        exact_curves[label] = run_constrained_curve(graph, times, holes, j_perp=float(exact_config["j_perp"]), jz=float(exact_config["jz"]), hopping_t=hopping, lambda_sd=exact_lambda)["data"]
                        surrogate_curves[label] = run_dtwa(graph, times, j_perp=float(exact_config["j_perp"]), jz=float(exact_config["jz"]), mobile_eta=eta, lambda_sd=surrogate_lambda, n_traj=int(surrogate["n_traj_per_phase_batch"]), initial_occupancy=occupancy, fixed_hole_count=len(holes), occupancy_seed=unit["occupancy_seed"], hole_path_seed=unit["hole_path_seed"], phase_batch_seed=unit["phase_batch_seed"])["data"]
                    for method, curves in [("exact", exact_curves), ("surrogate", surrogate_curves)]:
                        difference = float(np.max(np.abs(curves["static_only"] - curves[compared_label])))
                        rows.append({"case_id": case["id"], "method": method, "comparison_label": compared_label, "occupancy_idx": occupancy_idx, "path_idx": path_idx, "phase_idx": phase_idx, **unit, "max_abs_full_curve_difference": difference, "passed": bool(difference <= tolerance)})
    frame = pd.DataFrame(rows); passed = bool(len(frame) > 0 and frame.passed.all())
    payload = {"stage": "stage5c2gR_paired_calibration_invariants", "status": "PAIRED_CALIBRATION_INVARIANTS_PASSED" if passed else "PAIRED_CALIBRATION_INVARIANTS_FAILED", "passed": passed, "protocol_candidate_sha256": lock["candidate_sha256"], "source_tree_sha256": lock["candidate_payload"]["source_tree_sha256"], "maximum_observed_difference": float(frame.max_abs_full_curve_difference.max()), "tolerance": tolerance, "locked_at_utc": datetime.now(timezone.utc).isoformat()}
    payload["lock_sha256"] = sha256_payload(payload)
    output = ROOT / args.out; output.mkdir(parents=True, exist_ok=True); frame.to_csv(output / "paired_zero_coupling_units.csv", index=False)
    target = output / ("LOCKED.json" if passed else "FAILED.json"); target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    if not passed: raise SystemExit("G1 failed; transport calibration and every downstream simulation remain blocked")


if __name__ == "__main__": main()
