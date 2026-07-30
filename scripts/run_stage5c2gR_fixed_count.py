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
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "scripts"))
from haxs.lattice.graphs import hypercubic_lattice
from haxs.methods.dtwa import run_dtwa
from haxs.models.controls import ControlProtocol
from haxs.validation.topology import random_walk_displacement, topology_descriptors
from stage5c2gR_chunks import create_chunk_manifest, validate_chunk_manifest
from stage5c2gR_common import assert_protocol_locked, assert_supervisor_validation_approval, checked_lock, load_yaml, planned_fixed_count_registry, sha256_payload


def array_hash(value) -> str:
    return hashlib.sha256(np.asarray(value, dtype=np.int8).tobytes()).hexdigest()


def run_id(row: dict, hole_count: int) -> str:
    return f"stage5c2gR_h{hole_count:02d}_o{int(row['occupancy_idx']):03d}_p{int(row['path_idx']):02d}_b{int(row['phase_idx']):02d}_{row['label']}"


def main() -> None:
    raise SystemExit("BLOCKED LEGACY ROUTE: Stage 5C.2G-R fixed-hole execution is not authorized")
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/stage5c2gR/fixed_count.yaml")
    parser.add_argument("--protocol", default="configs/stage5c2gR/protocol.yaml")
    parser.add_argument("--holes", type=int, required=True)
    parser.add_argument("--supervisor-approval", required=True)
    parser.add_argument("--occupancy-start", type=int, default=0)
    parser.add_argument("--occupancy-stop", type=int)
    parser.add_argument("--out", default="results/stage5c2gR/fixed_count")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    protocol_lock = assert_protocol_locked(protocol_path=args.protocol)
    mapping = checked_lock("results/stage5c2gR/mobility_mapping/LOCKED.json", "PASSED_AND_FROZEN", protocol_lock)
    checked_lock("results/stage5c2gR/validity_tolerances/LOCKED.json", "CALIBRATION_PASSED_AND_TOLERANCES_FROZEN", protocol_lock)
    validity_gate = assert_supervisor_validation_approval(args.supervisor_approval, protocol_lock)
    raw = load_yaml(args.config); stage = raw["stage5c2gR_fixed_count"]; model = raw["model"]; dtwa = raw["dtwa"]
    counts = [int(value) for value in stage["fixed_hole_counts"]]
    if args.holes not in counts: raise ValueError("hole count is not preregistered")
    total = int(stage["occupancies_per_count"]); start = max(0, args.occupancy_start); stop = min(total, args.occupancy_stop if args.occupancy_stop is not None else total)
    if not 0 <= start < stop <= total: raise ValueError("invalid occupancy range")
    plan = planned_fixed_count_registry(raw, args.holes)
    selected = plan[plan.occupancy_idx.between(start, stop - 1)]
    if args.dry_run:
        print(json.dumps({"stage": stage["stage"], "holes": args.holes, "occupancy_range": [start, stop], "label_runs": len(selected), "protocol_candidate_sha256": protocol_lock["candidate_sha256"], "validity_gate_sha256": validity_gate["gate_sha256"], "supervisor_approval_verified": True, "production_started": False}, indent=2)); return

    shape = tuple(int(value) for value in stage["shape"]); graph = hypercubic_lattice(shape, raw["lattice"]["periodic"])
    times = np.linspace(0.0, float(dtwa["t_max"]), int(dtwa["n_steps"])); fixed_index = int(np.argmin(np.abs(times - float(stage["fixed_time"]))))
    control = ControlProtocol(enabled=False, jz_initial=float(model["jz"]), final_time=float(times[-1]))
    config_hash = sha256_payload(raw)
    count_root = ROOT / args.out / protocol_lock["candidate_sha256"][:16] / f"holes_{args.holes:02d}"; chunks = count_root / "chunks"; chunks.mkdir(parents=True, exist_ok=True)

    for occupancy_idx in range(start, stop):
        units = plan[plan.occupancy_idx == occupancy_idx].sort_values(["path_idx", "phase_idx", "label"])
        expected_ids = [run_id(row, args.holes) for row in units.to_dict("records")]
        prefix = chunks / f"occ_{occupancy_idx:03d}"
        files = {role: prefix.with_name(prefix.name + f"_{role}.csv") for role in ["curves", "finals", "registry", "attempts"]}
        manifest_path = prefix.with_name(prefix.name + "_manifest.json")
        if args.resume and manifest_path.is_file():
            validate_chunk_manifest(manifest_path, expected_ids, protocol_lock["candidate_sha256"], config_hash)
            print(f"holes={args.holes} occupancy={occupancy_idx}: verified complete checkpoint; skipping"); continue
        curves, finals, registry, attempts = [], [], [], []
        for unit in units.to_dict("records"):
            label = str(unit["label"]); eta = 0.0 if label == "static_only" else float(mapping["best_eta"]); lambda_sd = 0.0 if label == "static_only" else float(model["lambda_sd"])
            identifier = run_id(unit, args.holes); started = time.perf_counter(); attempt = {"run_id": identifier, "status": "started", "error": ""}
            try:
                result = run_dtwa(graph, times, j_perp=float(model["j_perp"]), jz=float(model["jz"]), fixed_hole_count=args.holes, mobile_eta=eta, lambda_sd=lambda_sd, n_traj=int(stage["n_traj"]), seed=int(unit["phase_batch_seed"]), control=control, occupancy_seed=int(unit["occupancy_seed"]), hole_path_seed=int(unit["hole_path_seed"]), phase_batch_seed=int(unit["phase_batch_seed"]))
                initial = np.asarray(result["initial_occupancy"], dtype=bool); descriptors = topology_descriptors(graph, initial); elapsed = time.perf_counter() - started
                common = {"stage": "stage5c2gR", "block": "fixed_count", "hole_count": args.holes, "shape": "x".join(map(str, shape)), "label": label, "occupancy_idx": occupancy_idx, "path_idx": int(unit["path_idx"]), "phase_idx": int(unit["phase_idx"]), **{key: unit[key] for key in ["block_id", "occupancy_realization_id", "hole_path_realization_id", "phase_batch_realization_id", "occupancy_seed", "hole_path_seed", "phase_batch_seed"]}, "occupancy_hash": array_hash(initial), "simulator_path_hash": array_hash(result["occupancy_trajectory"]), "config_sha256": config_hash, "protocol_candidate_sha256": protocol_lock["candidate_sha256"], "mapping_lock_sha256": mapping["lock_sha256"], "validity_gate_sha256": validity_gate["gate_sha256"], "run_id": identifier, **{f"initial_{key}": value for key, value in descriptors.items()}, **random_walk_displacement(graph, result["occupancy_trajectory"])}
                frame = pd.DataFrame(result["data"], columns=result["columns"])
                for key, value in common.items(): frame[key] = value
                curves.append(frame); fixed = frame.iloc[fixed_index]; best = frame.iloc[int(np.nanargmin(frame.xi2_db.to_numpy(float)))]
                finals.append({**common, "fixed_time": float(fixed.time), "xi2_db_fixed": float(fixed.xi2_db), "xi2_db_min": float(best.xi2_db), "time_at_min": float(best.time), "runtime_seconds": elapsed})
                registry.append(common); attempt.update({"status": "completed", "runtime_seconds": elapsed})
            except Exception as error:
                attempt.update({"status": "failed", "runtime_seconds": time.perf_counter() - started, "error": repr(error)}); attempts.append(attempt); pd.DataFrame(attempts).to_csv(files["attempts"], index=False); raise
            attempts.append(attempt)
        pd.concat(curves, ignore_index=True).to_csv(files["curves"], index=False); pd.DataFrame(finals).to_csv(files["finals"], index=False); pd.DataFrame(registry).to_csv(files["registry"], index=False); pd.DataFrame(attempts).to_csv(files["attempts"], index=False)
        manifest = create_chunk_manifest(f"holes_{args.holes:02d}_occ_{occupancy_idx:03d}", files, expected_ids, protocol_lock["candidate_sha256"], config_hash)
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print(f"holes={args.holes} occupancy={occupancy_idx}: checkpoint complete and hashed")

    manifests = []
    for occupancy_idx in range(total):
        units = plan[plan.occupancy_idx == occupancy_idx].sort_values(["path_idx", "phase_idx", "label"]); expected_ids = [run_id(row, args.holes) for row in units.to_dict("records")]
        path = chunks / f"occ_{occupancy_idx:03d}_manifest.json"
        if not path.is_file():
            print(f"holes={args.holes}: partial campaign; deterministic merge withheld"); return
        manifests.append(validate_chunk_manifest(path, expected_ids, protocol_lock["candidate_sha256"], config_hash))
    for role, filename in [("curves", "stage5c2gR_fixed_count_curves_all.csv"), ("finals", "stage5c2gR_fixed_count_finals.csv"), ("registry", "stage5c2gR_fixed_count_seed_registry.csv"), ("attempts", "stage5c2gR_fixed_count_attempt_ledger.csv")]:
        paths = [chunks / manifest["files"][role]["path"] for manifest in manifests]
        merged = pd.concat([pd.read_csv(path) for path in paths], ignore_index=True)
        if role != "curves" and (merged.run_id.duplicated().any() or set(merged.run_id.astype(str)) != set(plan.apply(lambda row: run_id(row, args.holes), axis=1))): raise RuntimeError(f"deterministic {role} merge ID check failed")
        merged.to_csv(count_root / filename, index=False)
    (count_root / "stage5c2gR_fixed_count_manifest.json").write_text(json.dumps({"stage": stage["stage"], "status": "COMPLETE", "hole_count": args.holes, "protocol_candidate_sha256": protocol_lock["candidate_sha256"], "config_sha256": config_hash, "chunk_manifest_sha256s": [manifest["manifest_sha256"] for manifest in manifests], "all_attempts_completed": True}, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
