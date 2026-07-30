#!/usr/bin/env python
from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "scripts"))
from haxs.lattice.graphs import hypercubic_lattice
from haxs.lattice.occupancy import sample_fixed_count
from haxs.methods.constrained_spin_hole import run_constrained_curve
from haxs.methods.dtwa import run_dtwa
from stage5c2gR2_common import assert_protocol_locked, canonical_config, physical_unit, plan_g1, production_label_parameters
from stage5c2gR2_state import atomic_write_json, build_raw_manifest, verify_gate_state, write_gate_state


def initial_holes(case: dict, occupancy_idx: int, seed: int, n_sites: int) -> list[int]:
    if occupancy_idx == 0: return [int(value) for value in case["holes"]]
    occupancy = sample_fixed_count(n_sites, len(case["holes"]), seed)
    return np.flatnonzero(~occupancy).astype(int).tolist()


def main() -> None:
    raise SystemExit("REJECTED: official Stage 5C.2G-R2 G1 is forbidden; use supervisor-accepted Stage 5C.2G-R3.1 with an exact structured receipt")
    if len(sys.argv) != 1: raise SystemExit("R2 G1 accepts no command-line configuration or output overrides")
    lock = assert_protocol_locked(); raw, config_sha, plan_sha = canonical_config("G1", lock); stage = raw["stage5c2gR2_G1"]; plan = plan_g1(raw)
    attempt_id = uuid.uuid4().hex; attempt_root = ROOT / "results/stage5c2gR2/artifacts/G1" / attempt_id; attempt_root.mkdir(parents=True, exist_ok=False)
    write_gate_state("G1", "RUNNING", lock, config_sha, plan_sha, attempt_id)
    curves, comparisons, registry, attempts = [], [], [], []
    try:
        times = np.linspace(float(stage["times"]["start"]), float(stage["times"]["stop"]), int(stage["times"]["points"]))
        cases = {case["id"]: case for case in stage["cases"]}; grouped = {}
        for row in plan:
            key = (row["case_id"], row["occupancy_idx"], row["path_idx"], row["phase_idx"]); grouped.setdefault(key, []).append(row)
        for (case_id, occupancy_idx, path_idx, phase_idx), planned_rows in grouped.items():
            case = cases[case_id]; graph = hypercubic_lattice(tuple(case["shape"]), False); unit = physical_unit(stage["namespace_uuid"], "G1", case_id, occupancy_idx, path_idx, phase_idx)
            holes = initial_holes(case, occupancy_idx, unit["occupancy_seed"], graph.n_sites); occupancy = np.ones(graph.n_sites, dtype=bool); occupancy[holes] = False
            method_curves: dict[str, dict[str, np.ndarray]] = {"exact": {}, "surrogate": {}}
            for label in case["labels"]:
                hopping, exact_lambda, eta, surrogate_lambda = production_label_parameters(label, stage["model"], case.get("overrides"))
                exact_result = run_constrained_curve(graph, times, holes, j_perp=float(stage["model"]["j_perp"]), jz=float(stage["model"]["jz"]), hopping_t=hopping, lambda_sd=exact_lambda)
                surrogate_result = run_dtwa(graph, times, j_perp=float(stage["model"]["j_perp"]), jz=float(stage["model"]["jz"]), mobile_eta=eta, lambda_sd=surrogate_lambda, n_traj=int(stage["n_traj_per_phase_batch"]), initial_occupancy=occupancy, fixed_hole_count=len(holes), occupancy_seed=unit["occupancy_seed"], hole_path_seed=unit["hole_path_seed"], phase_batch_seed=unit["phase_batch_seed"])
                method_curves["exact"][label] = np.asarray(exact_result["data"], dtype=float); method_curves["surrogate"][label] = np.asarray(surrogate_result["data"], dtype=float)
                for method, result in [("exact", exact_result), ("surrogate", surrogate_result)]:
                    frame = pd.DataFrame(result["data"], columns=result["columns"])
                    frame.insert(0, "method", method); frame.insert(0, "label", label); frame.insert(0, "case_id", case_id)
                    for key, value in {"occupancy_idx": occupancy_idx, "path_idx": path_idx, "phase_idx": phase_idx, **unit}.items(): frame[key] = value
                    curves.append(frame)
            comparison_label = [label for label in case["labels"] if label != "static_only"][0]
            for planned in planned_rows:
                method = planned["method"]; difference = float(np.max(np.abs(method_curves[method]["static_only"] - method_curves[method][comparison_label])))
                row = {**planned, "max_abs_full_curve_difference": difference, "tolerance": float(stage["tolerance_max_abs_full_curve_difference"]), "passed": difference <= float(stage["tolerance_max_abs_full_curve_difference"])}
                comparisons.append(row); registry.append(planned); attempts.append({"comparison_id": planned["comparison_id"], "status": "completed"})
        comparison_frame = pd.DataFrame(comparisons)
        if len(comparison_frame) != int(stage["expected_comparison_rows"]) or not comparison_frame.passed.all(): raise RuntimeError("canonical G1 equality or expected-row gate failed")
        files = {"curves": attempt_root / "g1_curves.csv", "comparisons": attempt_root / "g1_comparisons.csv", "registry": attempt_root / "g1_registry.csv", "attempts": attempt_root / "g1_attempts.csv"}
        pd.concat(curves, ignore_index=True).to_csv(files["curves"], index=False); comparison_frame.to_csv(files["comparisons"], index=False); pd.DataFrame(registry).to_csv(files["registry"], index=False); pd.DataFrame(attempts).to_csv(files["attempts"], index=False)
        expected_ids = [row["comparison_id"] for row in plan]; observed_ids = comparison_frame.comparison_id.astype(str).tolist()
        manifest = build_raw_manifest("G1", attempt_root, files, expected_ids, observed_ids, lock, config_sha, plan_sha, attempt_id); manifest_path = attempt_root / "MANIFEST.json"; atomic_write_json(manifest_path, manifest)
        state = write_gate_state("G1", "PASSED", lock, config_sha, plan_sha, attempt_id, str(manifest_path.relative_to(ROOT)), manifest["manifest_sha256"])
        verify_gate_state("G1", lock)
        print(json.dumps({"gate": "G1", "status": "PASSED", "attempt_id": attempt_id, "state_sha256": state["state_sha256"], "manifest_sha256": manifest["manifest_sha256"], "rows": len(comparison_frame), "maximum_difference": float(comparison_frame.max_abs_full_curve_difference.max()), "next": "STOP_AND_RETURN_FOR_SUPERVISORY_REVIEW"}, indent=2))
    except Exception as error:
        write_gate_state("G1", "FAILED", lock, config_sha, plan_sha, attempt_id, error=repr(error)); raise


if __name__ == "__main__": main()
