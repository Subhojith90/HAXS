#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from haxs.io.result_store import save_dataframe, save_json
from haxs.lattice.graphs import hypercubic_lattice
from haxs.methods.dtwa import run_dtwa
from haxs.models.controls import ControlProtocol
from haxs.validation.topology import random_walk_displacement, topology_descriptors
from stage5c2g_common import assert_protocol_locked, load_yaml, planned_fixed_count_registry, sha256_payload


def label_parameters(label: str, model: dict) -> tuple[float, float]:
    if label == "static_only":
        return 0.0, 0.0
    if label == "mobile_plus_spin_density":
        return float(model["mobile_eta"]), float(model["lambda_sd"])
    raise ValueError(f"unsupported fixed-count label: {label}")


def array_hash(array) -> str:
    return hashlib.sha256(np.asarray(array, dtype=np.int8).tobytes()).hexdigest()


def main() -> None:
    raise SystemExit("REJECTED LEGACY ROUTE: Stage 5C.2G fixed-hole execution is disabled")
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/stage5c2g/fixed_count.yaml")
    parser.add_argument("--holes", type=int, required=True)
    parser.add_argument("--occupancy-start", type=int, default=0)
    parser.add_argument("--occupancy-stop", type=int)
    parser.add_argument("--out", default="results/stage5c2g/fixed_count")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    lock = assert_protocol_locked()
    raw = load_yaml(args.config)
    stage, model, dtwa = raw["stage5c2g_fixed_count"], raw["model"], raw["dtwa"]
    if args.holes not in [int(value) for value in stage["fixed_hole_counts"]]:
        raise ValueError("hole count is not preregistered")
    total_occupancies = int(stage["occupancies_per_count"])
    start = max(0, int(args.occupancy_start))
    stop = min(total_occupancies, int(args.occupancy_stop) if args.occupancy_stop is not None else total_occupancies)
    if not 0 <= start < stop <= total_occupancies:
        raise ValueError("invalid occupancy checkpoint range")
    plan = planned_fixed_count_registry(raw, args.holes)
    selected = plan[plan.occupancy_idx.between(start, stop - 1)]
    if args.dry_run:
        print(json.dumps({"stage": stage["stage"], "holes": args.holes, "occupancy_range": [start, stop], "simulator_runs": len(selected), "n_traj": stage["n_traj"], "protocol_candidate_sha256": lock["candidate_sha256"], "production_started": False}, indent=2))
        return

    shape = tuple(int(value) for value in stage["shape"])
    graph = hypercubic_lattice(shape, raw.get("lattice", {}).get("periodic", False))
    times = np.linspace(0.0, float(dtwa["t_max"]), int(dtwa["n_steps"]))
    fixed_idx = int(np.argmin(np.abs(times - float(stage["fixed_time"]))))
    control = ControlProtocol(enabled=False, jz_initial=float(model["jz"]), final_time=float(times[-1]))
    config_hash = sha256_payload(raw)
    count_root = ROOT / args.out / f"holes_{args.holes:02d}"
    chunks = count_root / "chunks"
    chunks.mkdir(parents=True, exist_ok=True)

    for occupancy_idx in range(start, stop):
        prefix = chunks / f"occ_{occupancy_idx:03d}"
        expected = [prefix.with_name(prefix.name + suffix) for suffix in ("_curves.csv", "_finals.csv", "_registry.csv", "_attempts.csv")]
        if args.resume and all(path.is_file() for path in expected):
            print(f"holes={args.holes} occupancy={occupancy_idx}: checkpoint complete; skipping")
            continue
        units = plan[plan.occupancy_idx == occupancy_idx].sort_values(["path_idx", "phase_idx", "label"])
        curves, finals, registry, attempts = [], [], [], []
        for unit in units.to_dict("records"):
            label = str(unit["label"])
            mobile_eta, lambda_sd = label_parameters(label, model)
            run_id = f"stage5c2g_h{args.holes:02d}_occ{occupancy_idx:03d}_path{int(unit['path_idx']):02d}_phase{int(unit['phase_idx']):02d}_{label}"
            generating_hash = sha256_payload({"config_hash": config_hash, "protocol_candidate_sha256": lock["candidate_sha256"], **unit})
            attempt = {"run_id": run_id, "hole_count": args.holes, "status": "started", "error": ""}
            started = time.perf_counter()
            try:
                result = run_dtwa(
                    graph, times, j_perp=float(model["j_perp"]), jz=float(model["jz"]),
                    fixed_hole_count=args.holes, mobile_eta=mobile_eta, lambda_sd=lambda_sd,
                    n_traj=int(stage["n_traj"]), seed=int(unit["phase_batch_seed"]), control=control,
                    occupancy_seed=int(unit["occupancy_seed"]), hole_path_seed=int(unit["hole_path_seed"]),
                    phase_batch_seed=int(unit["phase_batch_seed"]),
                )
                elapsed = time.perf_counter() - started
                initial = np.asarray(result["initial_occupancy"], dtype=bool)
                occupancy_hash = array_hash(initial)
                simulator_path_hash = array_hash(result["occupancy_trajectory"])
                descriptors = topology_descriptors(graph, initial)
                displacement = random_walk_displacement(graph, result["occupancy_trajectory"])
                common = {
                    "stage": "stage5c2g", "block": "fixed_count", "hole_count": args.holes,
                    "shape": "x".join(map(str, shape)), "N": graph.n_sites, "label": label,
                    "occupancy_idx": occupancy_idx, "path_idx": int(unit["path_idx"]), "phase_idx": int(unit["phase_idx"]),
                    "occupancy_seed": int(unit["occupancy_seed"]), "hole_path_seed": int(unit["hole_path_seed"]),
                    "phase_batch_seed": int(unit["phase_batch_seed"]), "occupancy_hash": occupancy_hash,
                    "path_hash": unit["path_realization_id"], "simulator_path_hash": simulator_path_hash,
                    "occupancy_realization_id": unit["occupancy_realization_id"], "path_realization_id": unit["path_realization_id"],
                    "phase_realization_id": unit["phase_realization_id"], "parent_config_hash": config_hash,
                    "generating_config_hash": generating_hash, "protocol_candidate_sha256": lock["candidate_sha256"],
                    "run_id": run_id, **{f"initial_{key}": value for key, value in descriptors.items()}, **displacement,
                }
                frame = pd.DataFrame(result["data"], columns=result["columns"])
                for key, value in common.items():
                    frame[key] = value
                curves.append(frame)
                fixed = frame.iloc[fixed_idx]
                best = frame.iloc[int(np.nanargmin(frame.xi2_db.to_numpy(float)))]
                finals.append({**common, "fixed_time": float(times[fixed_idx]), "xi2_db_fixed": float(fixed.xi2_db),
                               "xi2_db_min": float(best.xi2_db), "time_at_min": float(best.time),
                               "N_eff_fixed": float(fixed.N_eff), "active_bonds_fixed": float(fixed.active_bonds),
                               "runtime_seconds": elapsed})
                registry.append(common)
                attempt.update({"status": "completed", "runtime_seconds": elapsed})
            except Exception as error:
                attempt.update({"status": "failed", "runtime_seconds": time.perf_counter() - started, "error": repr(error)})
                attempts.append(attempt)
                pd.DataFrame(attempts).to_csv(prefix.with_name(prefix.name + "_attempts.csv"), index=False)
                raise
            attempts.append(attempt)
        save_dataframe(prefix.with_name(prefix.name + "_curves.csv"), pd.concat(curves, ignore_index=True), raw)
        save_dataframe(prefix.with_name(prefix.name + "_finals.csv"), pd.DataFrame(finals), raw)
        save_dataframe(prefix.with_name(prefix.name + "_registry.csv"), pd.DataFrame(registry), raw)
        pd.DataFrame(attempts).to_csv(prefix.with_name(prefix.name + "_attempts.csv"), index=False)
        print(f"holes={args.holes} occupancy={occupancy_idx}: checkpoint complete")

    def merge(suffix: str, filename: str) -> None:
        paths = sorted(chunks.glob(f"occ_*_{suffix}.csv"))
        if paths:
            pd.concat([pd.read_csv(path) for path in paths], ignore_index=True).to_csv(count_root / filename, index=False)

    merge("curves", "stage5c2g_fixed_count_curves_all.csv")
    merge("finals", "stage5c2g_fixed_count_finals.csv")
    merge("registry", "stage5c2g_fixed_count_seed_registry.csv")
    merge("attempts", "stage5c2g_fixed_count_attempt_ledger.csv")
    save_json(count_root / "stage5c2g_fixed_count_manifest.json", {"stage": stage["stage"], "hole_count": args.holes, "config": args.config, "config_hash": config_hash, "protocol_candidate_sha256": lock["candidate_sha256"], "claim_scope": stage["claim_scope"]})


if __name__ == "__main__":
    main()
