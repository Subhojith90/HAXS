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
from haxs.io.hashes import hash_dict
from haxs.io.result_store import save_dataframe, save_json
from haxs.lattice.graphs import hypercubic_lattice
from haxs.methods.dtwa import run_dtwa
from haxs.models.controls import ControlProtocol
from stage2_common import load_raw_config
from stage5c2f_common import config_hash, planned_registry, sha_array


def label_params(label: str, model: dict) -> dict:
    if label == "static_only":
        return {"mobile_eta": 0.0, "lambda_sd": 0.0}
    if label == "mobile_plus_spin_density":
        return {"mobile_eta": float(model["mobile_eta"]), "lambda_sd": float(model["lambda_sd"])}
    raise ValueError(f"unsupported Stage 5C.2F label: {label}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/stage5c2f/primary_lock.yaml")
    ap.add_argument("--locked-confirmation")
    ap.add_argument("--out", default="results/stage5c2f/primary")
    ap.add_argument("--occupancy-start", type=int, default=0)
    ap.add_argument("--occupancy-stop", type=int)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    raw = load_raw_config(args.config)
    st, model, dtwa = raw["stage5c2f"], raw["model"], raw["dtwa"]
    if st["preregistered_design"] != "balanced_fresh":
        raise ValueError("this runner is locked to the preregistered balanced_fresh design")
    confirmation = ROOT / (args.locked_confirmation or st["locked_confirmation"])
    required_confirmation = ["stage5c2d_finals.csv", "stage5c2d_curves_all.csv", "stage5c2d_seed_registry.csv", "stage5c2d_block_manifest.json"]
    missing = [name for name in required_confirmation if not (confirmation / name).is_file()]
    if missing:
        raise FileNotFoundError(f"frozen confirmation is incomplete: {missing}")

    registry_plan = planned_registry(raw)
    n_occ = int(st["design"]["occupancies"])
    start = max(0, args.occupancy_start)
    stop = min(n_occ, args.occupancy_stop if args.occupancy_stop is not None else n_occ)
    if not 0 <= start < stop <= n_occ:
        raise ValueError(f"invalid occupancy range [{start}, {stop}) for I={n_occ}")
    if args.dry_run:
        print(json.dumps({
            "stage": "stage5c2f_primary_lock_dry_run",
            "design": st["preregistered_design"],
            "shape": st["shape"],
            "occupancy_range": [start, stop],
            "paired_cells": (stop - start) * int(st["design"]["paths_per_occupancy"]) * int(st["design"]["phase_batches_per_path"]),
            "simulator_runs": len(registry_plan[registry_plan.occupancy_idx.between(start, stop - 1)]),
            "n_traj": int(st["n_traj"]),
            "config_hash": config_hash(raw),
            "production_started": False,
        }, indent=2))
        return

    out = ROOT / args.out
    chunks = out / "chunks"
    chunks.mkdir(parents=True, exist_ok=True)
    shape = tuple(st["shape"])
    graph = hypercubic_lattice(shape, raw.get("lattice", {}).get("periodic", False))
    times = np.linspace(0, float(dtwa["t_max"]), int(dtwa["n_steps"]))
    fixed_idx = max(0, min(len(times) - 1, int(round(float(st["fixed_time_fraction"]) * (len(times) - 1)))))
    fixed_time = float(times[fixed_idx])
    ctrl = ControlProtocol(enabled=False, jz_initial=float(model["jz"]), final_time=float(times[-1]))
    parent_hash = config_hash(raw)

    for oi in range(start, stop):
        prefix = chunks / f"occ_{oi:03d}"
        expected = [prefix.with_name(prefix.name + suffix) for suffix in ("_finals.csv", "_curves.csv", "_registry.csv", "_attempts.csv")]
        if args.resume and all(path.is_file() for path in expected):
            print(f"occupancy {oi}: complete checkpoint found; skipping")
            continue
        plan = registry_plan[registry_plan.occupancy_idx == oi].sort_values(["path_idx", "phase_idx", "label"])
        curves, finals, registry, attempts = [], [], [], []
        for unit in plan.to_dict("records"):
            label = unit["label"]
            lp = label_params(label, model)
            generating_hash = hash_dict({
                "parent_config_hash": parent_hash,
                "occupancy_idx": oi,
                "path_idx": unit["path_idx"],
                "phase_idx": unit["phase_idx"],
                "label": label,
                "occupancy_seed": unit["occupancy_seed"],
                "hole_path_seed": unit["hole_path_seed"],
                "phase_batch_seed": unit["phase_batch_seed"],
            })
            run_id = f"stage5c2f_primary_occ{oi:03d}_path{unit['path_idx']:02d}_phase{unit['phase_idx']:02d}_{label}"
            attempt = {"run_id": run_id, "status": "started", "error": ""}
            t0 = time.perf_counter()
            try:
                res = run_dtwa(
                    graph, times, j_perp=float(model["j_perp"]), jz=float(model["jz"]),
                    hole_fraction=float(model["hole_fraction"]), mobile_eta=lp["mobile_eta"],
                    lambda_sd=lp["lambda_sd"], n_traj=int(st["n_traj"]),
                    seed=int(unit["phase_batch_seed"]), control=ctrl,
                    occupancy_seed=int(unit["occupancy_seed"]),
                    hole_path_seed=int(unit["hole_path_seed"]),
                    phase_batch_seed=int(unit["phase_batch_seed"]),
                )
                elapsed = time.perf_counter() - t0
                occ_hash = sha_array(res["initial_occupancy"])
                simulator_path_hash = sha_array(res["occupancy_trajectory"])
                common = {
                    "stage": "stage5c2f", "block": "primary", "shape": "x".join(map(str, shape)),
                    "N": int(graph.n_sites), "label": label, "occupancy_idx": oi,
                    "path_idx": unit["path_idx"], "phase_idx": unit["phase_idx"],
                    "occupancy_seed": unit["occupancy_seed"], "hole_path_seed": unit["hole_path_seed"],
                    "phase_batch_seed": unit["phase_batch_seed"], "occupancy_hash": occ_hash,
                    "path_hash": unit["path_realization_id"], "simulator_path_hash": simulator_path_hash,
                    "occupancy_realization_id": unit["occupancy_realization_id"],
                    "path_realization_id": unit["path_realization_id"],
                    "phase_realization_id": unit["phase_realization_id"],
                    "parent_config_hash": parent_hash, "generating_config_hash": generating_hash,
                    "run_id": run_id,
                }
                frame = pd.DataFrame(res["data"], columns=res["columns"])
                for key, value in common.items():
                    frame[key] = value
                curves.append(frame)
                best_idx = int(np.nanargmin(frame["xi2_db"].to_numpy(float)))
                fixed, best = frame.iloc[fixed_idx], frame.iloc[best_idx]
                finals.append({**common, "n_holes": int(graph.n_sites - np.sum(res["initial_occupancy"])),
                               "xi2_db_fixed": float(fixed["xi2_db"]), "xi2_db_min": float(best["xi2_db"]),
                               "fixed_time": fixed_time, "time_at_min": float(best["time"]),
                               "N_eff_fixed": float(fixed["N_eff"]), "active_bonds_fixed": float(fixed["active_bonds"]),
                               "runtime_seconds": elapsed})
                registry.append(common)
                attempt.update({"status": "completed", "runtime_seconds": elapsed})
            except Exception as exc:
                attempt.update({"status": "failed", "runtime_seconds": time.perf_counter() - t0, "error": repr(exc)})
                attempts.append(attempt)
                pd.DataFrame(attempts).to_csv(prefix.with_name(prefix.name + "_attempts.csv"), index=False)
                raise
            attempts.append(attempt)
        save_dataframe(prefix.with_name(prefix.name + "_finals.csv"), pd.DataFrame(finals), raw)
        save_dataframe(prefix.with_name(prefix.name + "_curves.csv"), pd.concat(curves, ignore_index=True), raw)
        save_dataframe(prefix.with_name(prefix.name + "_registry.csv"), pd.DataFrame(registry), raw)
        pd.DataFrame(attempts).to_csv(prefix.with_name(prefix.name + "_attempts.csv"), index=False)
        print(f"occupancy {oi}: checkpoint complete")

    def merge(suffix: str, target: str) -> None:
        paths = sorted(chunks.glob(f"occ_*_{suffix}.csv"))
        if paths:
            pd.concat([pd.read_csv(path) for path in paths], ignore_index=True).to_csv(out / target, index=False)

    merge("finals", "stage5c2f_finals.csv")
    merge("curves", "stage5c2f_curves_all.csv")
    merge("registry", "stage5c2f_seed_registry.csv")
    merge("attempts", "stage5c2f_attempt_ledger.csv")
    save_json(out / "stage5c2f_primary_manifest.json", {
        "stage": "stage5c2f_primary_lock", "design": st["preregistered_design"],
        "config": args.config, "parent_config_hash": parent_hash, "occupancy_range_completed": [start, stop],
        "locked_confirmation": str(confirmation.relative_to(ROOT)), "claim_scope": st["claim_scope"],
    })


if __name__ == "__main__":
    main()
