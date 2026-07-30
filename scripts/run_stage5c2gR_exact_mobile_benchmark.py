#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from haxs.lattice.graphs import hypercubic_lattice
from haxs.lattice.occupancy import sample_fixed_count
from haxs.methods.constrained_spin_hole import run_constrained_curve
from haxs.methods.dtwa import run_dtwa
from haxs.models.controls import ControlProtocol
from stage5c2gR_common import assert_protocol_locked, checked_lock, load_yaml, physical_random_unit, sha256_payload

UNIT_COLUMNS = ["block_id", "occupancy_realization_id", "hole_path_realization_id", "phase_batch_realization_id", "exact_initial_state_id", "occupancy_idx", "path_idx", "phase_idx"]


def case_holes(case: dict, occupancy_idx: int, occupancy_seed: int, n_sites: int) -> list[int]:
    if occupancy_idx == 0:
        return [int(value) for value in case["holes"]]
    occupancy = sample_fixed_count(n_sites, len(case["holes"]), occupancy_seed)
    return np.flatnonzero(~occupancy).astype(int).tolist()


def label_parameters(label: str, exact: dict, surrogate: dict, case: dict, mapped_eta: float) -> tuple[float, float, float, float]:
    hopping = float(case.get("hopping_t", exact["hopping_t"]))
    eta = float(case.get("mobile_eta", mapped_eta))
    exact_lambda = float(case.get("lambda_sd", exact["lambda_sd"]))
    surrogate_lambda = float(case.get("lambda_sd", surrogate["lambda_sd"]))
    if label == "static_only":
        return 0.0, 0.0, 0.0, 0.0
    if label == "mobile_only":
        return hopping, 0.0, eta, 0.0
    if label == "spin_density_only":
        return 0.0, exact_lambda, 0.0, surrogate_lambda
    if label == "combined":
        return hopping, exact_lambda, eta, surrogate_lambda
    raise ValueError(f"unknown validity label: {label}")


def main() -> None:
    raise SystemExit("BLOCKED LEGACY ROUTE: Stage 5C.2G-R benchmark execution is not authorized")
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/stage5c2gR/exact_mobile_benchmark.yaml")
    parser.add_argument("--protocol", default="configs/stage5c2gR/protocol.yaml")
    parser.add_argument("--split", choices=["calibration", "validation"], required=True)
    parser.add_argument("--out", default="results/stage5c2gR")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    protocol_lock = assert_protocol_locked(protocol_path=args.protocol)
    invariant_lock = checked_lock("results/stage5c2gR/calibration_invariants/LOCKED.json", "PAIRED_CALIBRATION_INVARIANTS_PASSED", protocol_lock)
    mapping = checked_lock("results/stage5c2gR/mobility_mapping/LOCKED.json", "PASSED_AND_FROZEN", protocol_lock)
    tolerance = None
    if args.split == "validation":
        tolerance = checked_lock("results/stage5c2gR/validity_tolerances/LOCKED.json", "CALIBRATION_PASSED_AND_TOLERANCES_FROZEN", protocol_lock)
        if tolerance.get("mobility_mapping_lock_sha256") != mapping["lock_sha256"]:
            raise RuntimeError("validity tolerance lock does not bind the current mobility mapping")
    raw = load_yaml(args.config)
    stage = raw["stage5c2gR_exact_benchmark"]
    cases = stage[f"{args.split}_cases"]
    hierarchy = stage["hierarchy"]
    total_units = sum(
        int(hierarchy["occupancy_replicates"]) * int(hierarchy["paths_per_occupancy"]) * int(hierarchy["phase_batches_per_path"]) * len(case.get("labels", stage["labels"]))
        for case in cases
    )
    if args.dry_run:
        print(json.dumps({"stage": stage["stage"], "split": args.split, "cases": [case["id"] for case in cases], "label_runs": total_units, "common_random_numbers": True, "protocol_candidate_sha256": protocol_lock["candidate_sha256"], "mapping_lock_sha256": mapping["lock_sha256"], "calibration_lock_passed": tolerance is not None if args.split == "validation" else None, "production_started": False}, indent=2))
        return

    times = np.linspace(float(stage["times"]["start"]), float(stage["times"]["stop"]), int(stage["times"]["points"]))
    exact_config, surrogate_config = stage["exact_model"], stage["surrogate"]
    namespace = str(stage["namespace_uuid"])
    output = ROOT / args.out / args.split
    output.mkdir(parents=True, exist_ok=True)
    exact_frames, surrogate_frames, density_rows, configuration_rows, attempts, registry = [], [], [], [], [], []
    exact_cache: dict[tuple, dict] = {}

    for case in cases:
        case_id = str(case["id"])
        shape = tuple(int(value) for value in case["shape"])
        graph = hypercubic_lattice(shape, periodic=False)
        labels = list(case.get("labels", stage["labels"]))
        for occupancy_idx in range(int(hierarchy["occupancy_replicates"])):
            occupancy_unit = physical_random_unit(namespace, args.split, case_id, occupancy_idx, 0, 0)
            holes = case_holes(case, occupancy_idx, occupancy_unit["occupancy_seed"], graph.n_sites)
            initial_occupancy = np.ones(graph.n_sites, dtype=bool); initial_occupancy[holes] = False
            for path_idx in range(int(hierarchy["paths_per_occupancy"])):
                for phase_idx in range(int(hierarchy["phase_batches_per_path"])):
                    unit = physical_random_unit(namespace, args.split, case_id, occupancy_idx, path_idx, phase_idx)
                    for label in labels:
                        hopping_t, exact_lambda, mobile_eta, surrogate_lambda = label_parameters(label, exact_config, surrogate_config, case, float(mapping["best_eta"]))
                        run_id = f"stage5c2gR_{args.split}_{case_id}_o{occupancy_idx:02d}_p{path_idx:02d}_b{phase_idx:02d}_{label}"
                        attempt = {"run_id": run_id, "case_id": case_id, "split": args.split, "label": label, "occupancy_idx": occupancy_idx, "path_idx": path_idx, "phase_idx": phase_idx, "status": "started", "error": ""}
                        started = time.perf_counter()
                        try:
                            exact_key = (case_id, occupancy_idx, label)
                            if exact_key not in exact_cache:
                                exact_cache[exact_key] = run_constrained_curve(graph, times, holes, j_perp=float(exact_config["j_perp"]), jz=float(exact_config["jz"]), hopping_t=hopping_t, lambda_sd=exact_lambda)
                            exact_result = exact_cache[exact_key]
                            common = {"case_id": case_id, "split": args.split, "label": label, "shape": "x".join(map(str, shape)), "n_holes": len(holes), "initial_holes": ";".join(map(str, holes)), "occupancy_idx": occupancy_idx, "path_idx": path_idx, "phase_idx": phase_idx, **unit, "protocol_candidate_sha256": protocol_lock["candidate_sha256"], "mapping_lock_sha256": mapping["lock_sha256"], "run_id": run_id}
                            exact_frame = pd.DataFrame(exact_result["data"], columns=exact_result["columns"])
                            exact_frame["method"] = "hard_core_bosonic_constrained_exact_krylov"
                            for key, value in common.items(): exact_frame[key] = value
                            exact_frame["hopping_t"] = hopping_t; exact_frame["lambda_sd"] = exact_lambda
                            exact_frame["basis_dimension"] = exact_result["basis_dimension"]
                            exact_frame["hamiltonian_hermiticity_error"] = exact_result["hamiltonian_hermiticity_error"]
                            exact_frames.append(exact_frame)

                            control = ControlProtocol(enabled=False, jz_initial=float(exact_config["jz"]), final_time=float(times[-1]))
                            surrogate_result = run_dtwa(graph, times, j_perp=float(exact_config["j_perp"]), jz=float(exact_config["jz"]), mobile_eta=mobile_eta, lambda_sd=surrogate_lambda, n_traj=int(surrogate_config["n_traj_per_phase_batch"]), seed=unit["phase_batch_seed"], control=control, fixed_hole_count=len(holes), initial_occupancy=initial_occupancy, occupancy_seed=unit["occupancy_seed"], hole_path_seed=unit["hole_path_seed"], phase_batch_seed=unit["phase_batch_seed"])
                            surrogate_frame = pd.DataFrame(surrogate_result["data"], columns=surrogate_result["columns"])
                            surrogate_frame["method"] = "stochastic_occupancy_mask_surrogate"
                            for key, value in common.items(): surrogate_frame[key] = value
                            surrogate_frame["mobile_eta"] = mobile_eta; surrogate_frame["lambda_sd"] = surrogate_lambda
                            surrogate_frames.append(surrogate_frame)

                            surrogate_density = (~np.asarray(surrogate_result["occupancy_trajectory"], dtype=bool)).astype(float)
                            for method, density in [("exact", exact_result["hole_density"]), ("surrogate", surrogate_density)]:
                                for time_index, time_value in enumerate(times):
                                    for site, value in enumerate(density[time_index]):
                                        density_rows.append({**common, "method": method, "time": float(time_value), "site": site, "hole_density": float(value)})
                            for time_index, time_value in enumerate(times):
                                exact_distribution = exact_result["hole_configuration_probabilities"][time_index]
                                for configuration, probability in exact_distribution.items():
                                    configuration_rows.append({**common, "method": "exact", "time": float(time_value), "hole_configuration": ";".join(map(str, configuration)), "probability": float(probability)})
                                surrogate_configuration = tuple(np.flatnonzero(~np.asarray(surrogate_result["occupancy_trajectory"][time_index], dtype=bool)).astype(int))
                                configuration_rows.append({**common, "method": "surrogate", "time": float(time_value), "hole_configuration": ";".join(map(str, surrogate_configuration)), "probability": 1.0})
                            registry.append({**common, "occupancy_seed": unit["occupancy_seed"], "hole_path_seed": unit["hole_path_seed"], "phase_batch_seed": unit["phase_batch_seed"]})
                            attempt.update({"status": "completed", "runtime_seconds": time.perf_counter() - started, "exact_basis_dimension": exact_result["basis_dimension"]})
                        except Exception as error:
                            attempt.update({"status": "failed", "runtime_seconds": time.perf_counter() - started, "error": repr(error)})
                            attempts.append(attempt)
                            pd.DataFrame(attempts).to_csv(output / "stage5c2gR_attempt_ledger.csv", index=False)
                            raise
                        attempts.append(attempt)

    if any(row["status"] != "completed" for row in attempts) or len(attempts) != total_units:
        raise RuntimeError("benchmark attempt ledger is incomplete")
    pd.concat(exact_frames, ignore_index=True).to_csv(output / "stage5c2gR_exact_curves.csv", index=False)
    pd.concat(surrogate_frames, ignore_index=True).to_csv(output / "stage5c2gR_surrogate_curves.csv", index=False)
    pd.DataFrame(density_rows).to_csv(output / "stage5c2gR_hole_density.csv", index=False)
    pd.DataFrame(configuration_rows).to_csv(output / "stage5c2gR_hole_configuration_history.csv", index=False)
    pd.DataFrame(registry).to_csv(output / "stage5c2gR_random_unit_registry.csv", index=False)
    pd.DataFrame(attempts).to_csv(output / "stage5c2gR_attempt_ledger.csv", index=False)
    manifest = {"stage": stage["stage"], "split": args.split, "config": args.config, "config_hash": sha256_payload(raw), "protocol_candidate_sha256": protocol_lock["candidate_sha256"], "source_tree_sha256": protocol_lock["candidate_payload"]["source_tree_sha256"], "calibration_invariant_lock_sha256": invariant_lock["lock_sha256"], "mapping_lock_sha256": mapping["lock_sha256"], "tolerance_lock_sha256": tolerance.get("lock_sha256") if tolerance else None, "expected_label_runs": total_units, "completed_label_runs": len(attempts), "all_attempts_completed": True, "claim_scope": stage["claim_scope"]}
    (output / "stage5c2gR_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
