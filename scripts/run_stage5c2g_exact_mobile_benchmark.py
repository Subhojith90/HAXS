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
from haxs.methods.constrained_spin_hole import run_constrained_curve
from haxs.methods.dtwa import run_dtwa
from haxs.models.controls import ControlProtocol
from stage5c2g_common import assert_protocol_locked, domain_seed, load_yaml, sha256_payload


def label_parameters(label: str, exact: dict, surrogate: dict, case: dict) -> tuple[float, float, float, float]:
    hopping = float(case.get("hopping_t", exact["hopping_t"]))
    eta = float(case.get("mobile_eta", surrogate["mobile_eta"]))
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


def require_tolerance_lock() -> dict:
    path = ROOT / "results/stage5c2g/validity_tolerances/LOCKED.json"
    if not path.is_file():
        raise RuntimeError("untouched validation is blocked until calibration tolerances are locked")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    raise SystemExit("REJECTED LEGACY ROUTE: Stage 5C.2G execution is disabled; use Stage 5C.2G-R2")
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/stage5c2g/exact_mobile_benchmark.yaml")
    parser.add_argument("--split", choices=["calibration", "validation"], required=True)
    parser.add_argument("--out", default="results/stage5c2g")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    protocol = assert_protocol_locked()
    tolerance = require_tolerance_lock() if args.split == "validation" else None
    if tolerance is not None and tolerance.get("protocol_candidate_sha256") != protocol["candidate_sha256"]:
        raise RuntimeError("validity tolerance lock belongs to a different protocol")
    raw = load_yaml(args.config)
    stage = raw["stage5c2g_exact_benchmark"]
    cases = stage[f"{args.split}_cases"]
    if args.dry_run:
        print(json.dumps({"stage": stage["stage"], "split": args.split, "cases": [case["id"] for case in cases], "labels": sum(len(case.get("labels", stage["labels"])) for case in cases), "protocol_candidate_sha256": protocol["candidate_sha256"], "tolerances_locked": tolerance is not None, "production_started": False}, indent=2))
        return
    times_config = stage["times"]
    times = np.linspace(float(times_config["start"]), float(times_config["stop"]), int(times_config["points"]))
    exact_config, surrogate_config = stage["exact_model"], stage["surrogate"]
    namespace = str(stage["namespace_uuid"])
    output = ROOT / args.out / args.split
    output.mkdir(parents=True, exist_ok=True)
    exact_frames, surrogate_frames, density_rows, history_rows, attempts = [], [], [], [], []

    for case in cases:
        case_id = str(case["id"])
        shape = tuple(int(value) for value in case["shape"])
        graph = hypercubic_lattice(shape, periodic=False)
        holes = [int(value) for value in case["holes"]]
        initial_occupancy = np.ones(graph.n_sites, dtype=bool)
        initial_occupancy[holes] = False
        for label in case.get("labels", stage["labels"]):
            hopping_t, exact_lambda, mobile_eta, surrogate_lambda = label_parameters(label, exact_config, surrogate_config, case)
            seed = domain_seed(namespace, args.split, "surrogate", case_id, label)
            run_id = f"stage5c2g_{args.split}_{case_id}_{label}"
            attempt = {"run_id": run_id, "case_id": case_id, "split": args.split, "label": label, "status": "started", "error": ""}
            started = time.perf_counter()
            try:
                exact_result = run_constrained_curve(
                    graph, times, holes, j_perp=float(exact_config["j_perp"]), jz=float(exact_config["jz"]),
                    hopping_t=hopping_t, lambda_sd=exact_lambda,
                )
                exact_frame = pd.DataFrame(exact_result["data"], columns=exact_result["columns"])
                exact_frame["method"] = "constrained_exact_krylov"
                exact_frame["case_id"] = case_id; exact_frame["split"] = args.split; exact_frame["label"] = label
                exact_frame["shape"] = "x".join(map(str, shape)); exact_frame["n_holes"] = len(holes)
                exact_frame["hopping_t"] = hopping_t; exact_frame["lambda_sd"] = exact_lambda
                exact_frame["basis_dimension"] = exact_result["basis_dimension"]
                exact_frame["hamiltonian_hermiticity_error"] = exact_result["hamiltonian_hermiticity_error"]
                exact_frame["protocol_candidate_sha256"] = protocol["candidate_sha256"]
                exact_frames.append(exact_frame)
                for time_index, time_value in enumerate(times):
                    for site, density in enumerate(exact_result["hole_density"][time_index]):
                        density_rows.append({"case_id": case_id, "split": args.split, "label": label, "time": float(time_value), "site": site, "hole_density": float(density)})
                    for configuration, probability in exact_result["hole_configuration_probabilities"][time_index].items():
                        history_rows.append({"case_id": case_id, "split": args.split, "label": label, "time": float(time_value), "hole_configuration": ";".join(map(str, configuration)), "probability": float(probability)})
                control = ControlProtocol(enabled=False, jz_initial=float(exact_config["jz"]), final_time=float(times[-1]))
                surrogate_result = run_dtwa(
                    graph, times, j_perp=float(exact_config["j_perp"]), jz=float(exact_config["jz"]),
                    mobile_eta=mobile_eta, lambda_sd=surrogate_lambda, n_traj=int(surrogate_config["n_traj"]),
                    seed=seed, control=control, fixed_hole_count=len(holes), initial_occupancy=initial_occupancy,
                    occupancy_seed=domain_seed(namespace, args.split, "occupancy", case_id),
                    hole_path_seed=domain_seed(namespace, args.split, "path", case_id, label),
                    phase_batch_seed=domain_seed(namespace, args.split, "phase", case_id, label),
                )
                surrogate_frame = pd.DataFrame(surrogate_result["data"], columns=surrogate_result["columns"])
                surrogate_frame["method"] = "stochastic_mask_surrogate"
                surrogate_frame["case_id"] = case_id; surrogate_frame["split"] = args.split; surrogate_frame["label"] = label
                surrogate_frame["shape"] = "x".join(map(str, shape)); surrogate_frame["n_holes"] = len(holes)
                surrogate_frame["mobile_eta"] = mobile_eta; surrogate_frame["lambda_sd"] = surrogate_lambda
                surrogate_frame["protocol_candidate_sha256"] = protocol["candidate_sha256"]
                surrogate_frames.append(surrogate_frame)
                attempt.update({"status": "completed", "runtime_seconds": time.perf_counter() - started, "exact_basis_dimension": exact_result["basis_dimension"]})
            except Exception as error:
                attempt.update({"status": "failed", "runtime_seconds": time.perf_counter() - started, "error": repr(error)})
                attempts.append(attempt)
                pd.DataFrame(attempts).to_csv(output / "stage5c2g_attempt_ledger.csv", index=False)
                raise
            attempts.append(attempt)
    pd.concat(exact_frames, ignore_index=True).to_csv(output / "stage5c2g_exact_curves.csv", index=False)
    pd.concat(surrogate_frames, ignore_index=True).to_csv(output / "stage5c2g_surrogate_curves.csv", index=False)
    pd.DataFrame(density_rows).to_csv(output / "stage5c2g_exact_hole_density.csv", index=False)
    pd.DataFrame(history_rows).to_csv(output / "stage5c2g_exact_hole_configuration_history.csv", index=False)
    pd.DataFrame(attempts).to_csv(output / "stage5c2g_attempt_ledger.csv", index=False)
    manifest = {"stage": stage["stage"], "split": args.split, "config": args.config, "config_hash": sha256_payload(raw), "protocol_candidate_sha256": protocol["candidate_sha256"], "tolerance_lock_sha256": tolerance.get("tolerance_lock_sha256") if tolerance else None, "claim_scope": stage["claim_scope"]}
    (output / "stage5c2g_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
