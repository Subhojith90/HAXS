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
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from haxs.lattice.graphs import hypercubic_lattice
from haxs.lattice.occupancy import sample_fixed_count
from haxs.methods.constrained_spin_hole import run_constrained_curve
from haxs.models.mobile_holes import mobile_occupancy_trajectory
from haxs.validation.transport import density_from_occupancy_trajectories, empirical_configuration_probabilities, transport_discrepancy
from stage5c2gR_common import assert_protocol_locked, checked_lock, load_yaml, physical_random_unit, sha256_payload


def initial_holes(case: dict, occupancy_idx: int, seed: int, n_sites: int) -> list[int]:
    if occupancy_idx == 0:
        return [int(value) for value in case["holes"]]
    occupancy = sample_fixed_count(n_sites, len(case["holes"]), seed)
    return np.flatnonzero(~occupancy).astype(int).tolist()


def summarize(discrepancy: dict, mask: np.ndarray) -> dict[str, float]:
    return {
        "density_l1_mean": float(np.mean(np.asarray(discrepancy["density_l1_by_time"])[mask])),
        "normalized_msd_rmse": float(np.sqrt(np.mean(np.asarray(discrepancy["normalized_msd_error"])[mask] ** 2))),
        "return_probability_rmse": float(np.sqrt(np.mean(np.asarray(discrepancy["return_probability_error"])[mask] ** 2))),
        "configuration_tv_mean": float(np.mean(np.asarray(discrepancy["configuration_tv_by_time"])[mask])),
    }


def main() -> None:
    raise SystemExit("BLOCKED LEGACY ROUTE: Stage 5C.2G-R G2 is not authorized")
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/stage5c2gR/exact_mobile_benchmark.yaml")
    parser.add_argument("--protocol", default="configs/stage5c2gR/protocol.yaml")
    parser.add_argument("--out", default="results/stage5c2gR/mobility_mapping")
    args = parser.parse_args()
    lock = assert_protocol_locked(protocol_path=args.protocol)
    invariant_lock = checked_lock("results/stage5c2gR/calibration_invariants/LOCKED.json", "PAIRED_CALIBRATION_INVARIANTS_PASSED", lock)
    benchmark = load_yaml(args.config)["stage5c2gR_exact_benchmark"]
    protocol = load_yaml(args.protocol)["stage5c2gR_protocol"]
    gates = protocol["transport_mapping_gates"]
    hierarchy = benchmark["hierarchy"]
    times = np.linspace(float(benchmark["times"]["start"]), float(benchmark["times"]["stop"]), int(benchmark["times"]["points"]))
    dt = float(times[1] - times[0])
    namespace = str(benchmark["namespace_uuid"])
    unit_rows, metric_rows = [], []
    cached_paths: dict[tuple, np.ndarray] = {}
    cached_exact: dict[tuple, dict] = {}

    for case in benchmark["transport_calibration_cases"]:
        graph = hypercubic_lattice(tuple(case["shape"]), False)
        for occupancy_idx in range(int(hierarchy["occupancy_replicates"])):
            base = physical_random_unit(namespace, "transport_calibration", case["id"], occupancy_idx, 0, 0)
            holes = initial_holes(case, occupancy_idx, base["occupancy_seed"], graph.n_sites)
            exact = run_constrained_curve(graph, times, holes, j_perp=float(benchmark["exact_model"]["j_perp"]), jz=float(benchmark["exact_model"]["jz"]), hopping_t=float(case["hopping_t"]), lambda_sd=0.0)
            cached_exact[(case["id"], occupancy_idx)] = exact
            for eta in [float(value) for value in gates["eta_grid"]]:
                paths = []
                for path_idx in range(int(hierarchy["transport_paths_per_occupancy"])):
                    unit = physical_random_unit(namespace, "transport_calibration", case["id"], occupancy_idx, path_idx, 0)
                    occupancy = np.ones(graph.n_sites, dtype=bool); occupancy[holes] = False
                    trajectory = mobile_occupancy_trajectory(graph, occupancy, len(times), eta, dt, unit["hole_path_seed"])
                    paths.append(trajectory)
                    unit_rows.append({"case_id": case["id"], "occupancy_idx": occupancy_idx, "path_idx": path_idx, "eta": eta, **unit})
                stack = np.asarray(paths, dtype=bool)
                cached_paths[(case["id"], occupancy_idx, eta)] = stack
                surrogate_density = density_from_occupancy_trajectories(stack)
                surrogate_configurations = empirical_configuration_probabilities(stack)
                discrepancy = transport_discrepancy(exact["hole_density"], surrogate_density, graph.coords, holes, exact["hole_configuration_probabilities"], surrogate_configurations)
                for window in [float(value) for value in gates["fitting_time_windows"]]:
                    mask = times <= window + 1e-12
                    metrics = summarize(discrepancy, mask)
                    loss = metrics["density_l1_mean"] + metrics["normalized_msd_rmse"] + metrics["return_probability_rmse"] + metrics["configuration_tv_mean"]
                    metric_rows.append({"case_id": case["id"], "occupancy_idx": occupancy_idx, "eta": eta, "window_stop": window, "loss": loss, **metrics})

    metrics = pd.DataFrame(metric_rows)
    aggregate = metrics.groupby(["eta", "window_stop"], as_index=False).mean(numeric_only=True)
    full_window = max(float(value) for value in gates["fitting_time_windows"])
    full = aggregate[np.isclose(aggregate.window_stop, full_window)].sort_values(["loss", "eta"])
    best = full.iloc[0]
    best_eta = float(best.eta)
    window_best = aggregate.loc[aggregate.groupby("window_stop").loss.idxmin(), ["window_stop", "eta", "loss"]].sort_values("window_stop")
    sensitivity = float(window_best.eta.max() - window_best.eta.min())

    generator = np.random.default_rng(int(gates["bootstrap_seed"]))
    bootstrap_best = []
    path_count = int(hierarchy["transport_paths_per_occupancy"])
    for _ in range(int(gates["bootstrap_replicates"])):
        sampled_losses = []
        draw = generator.integers(0, path_count, size=path_count)
        for eta in [float(value) for value in gates["eta_grid"]]:
            losses = []
            for case in benchmark["transport_calibration_cases"]:
                graph = hypercubic_lattice(tuple(case["shape"]), False)
                for occupancy_idx in range(int(hierarchy["occupancy_replicates"])):
                    base = physical_random_unit(namespace, "transport_calibration", case["id"], occupancy_idx, 0, 0)
                    holes = initial_holes(case, occupancy_idx, base["occupancy_seed"], graph.n_sites)
                    exact = cached_exact[(case["id"], occupancy_idx)]
                    stack = cached_paths[(case["id"], occupancy_idx, eta)][draw]
                    discrepancy = transport_discrepancy(exact["hole_density"], density_from_occupancy_trajectories(stack), graph.coords, holes, exact["hole_configuration_probabilities"], empirical_configuration_probabilities(stack))
                    summary = summarize(discrepancy, times <= full_window + 1e-12)
                    losses.append(summary["density_l1_mean"] + summary["normalized_msd_rmse"] + summary["return_probability_rmse"] + summary["configuration_tv_mean"])
            sampled_losses.append((float(np.mean(losses)), eta))
        bootstrap_best.append(min(sampled_losses)[1])

    pass_fields = {
        "density_l1_pass": bool(float(best.density_l1_mean) <= float(gates["density_l1_mean_maximum"])),
        "normalized_msd_pass": bool(float(best.normalized_msd_rmse) <= float(gates["normalized_msd_rmse_maximum"])),
        "return_probability_pass": bool(float(best.return_probability_rmse) <= float(gates["return_probability_rmse_maximum"])),
        "configuration_distribution_pass": bool(float(best.configuration_tv_mean) <= float(gates["configuration_tv_mean_maximum"])),
        "window_sensitivity_pass": bool(sensitivity <= float(gates["eta_window_sensitivity_maximum"])),
    }
    passed = all(pass_fields.values())
    payload = {
        "stage": "stage5c2gR_transport_mobility_mapping",
        "status": "PASSED_AND_FROZEN" if passed else "FAILED_NOT_FROZEN",
        "passed": passed,
        "protocol_candidate_sha256": lock["candidate_sha256"],
        "source_tree_sha256": lock["candidate_payload"]["source_tree_sha256"],
        "calibration_invariant_lock_sha256": invariant_lock["lock_sha256"],
        "calibration_cases": [case["id"] for case in benchmark["transport_calibration_cases"]],
        "validation_cases_inspected": [],
        "fitting_observables": ["hole_density", "mean_squared_displacement", "return_probability", "configuration_total_variation"],
        "forbidden_tuning_observables_used": [],
        "best_eta": best_eta,
        "exact_hopping_t": float(benchmark["exact_model"]["hopping_t"]),
        "eta_bootstrap_95_interval": [float(np.quantile(bootstrap_best, 0.025)), float(np.quantile(bootstrap_best, 0.975))],
        "eta_window_sensitivity": sensitivity,
        "best_metrics": {key: float(best[key]) for key in ["density_l1_mean", "normalized_msd_rmse", "return_probability_rmse", "configuration_tv_mean", "loss"]},
        "pass_fields": pass_fields,
        "locked_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    payload["lock_sha256"] = sha256_payload(payload)
    output = ROOT / args.out
    output.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(unit_rows).to_csv(output / "transport_random_unit_registry.csv", index=False)
    metrics.to_csv(output / "transport_calibration_metrics.csv", index=False)
    aggregate.to_csv(output / "transport_calibration_aggregate.csv", index=False)
    window_best.to_csv(output / "transport_window_sensitivity.csv", index=False)
    target = output / ("LOCKED.json" if passed else "FAILED.json")
    target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    if not passed:
        raise SystemExit("transport mapping failed; no mobility lock was created")


if __name__ == "__main__":
    main()
