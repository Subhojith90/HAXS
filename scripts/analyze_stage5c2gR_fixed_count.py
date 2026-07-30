#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2gR_common import assert_protocol_locked, load_yaml

PAIR = ["hole_count", "occupancy_realization_id", "hole_path_realization_id", "phase_batch_realization_id", "occupancy_idx", "path_idx", "phase_idx"]


def effects(frame: pd.DataFrame) -> pd.DataFrame:
    static = frame[frame.label == "static_only"][PAIR + ["xi2_db"]].rename(columns={"xi2_db": "static"})
    combined = frame[frame.label == "mobile_plus_spin_density"][PAIR + ["xi2_db"]].rename(columns={"xi2_db": "combined"})
    paired = static.merge(combined, on=PAIR, validate="one_to_one"); paired["effect_db"] = paired.static - paired.combined
    return paired


def draw_nested(array: np.ndarray, generator: np.random.Generator) -> float:
    occupancies, paths, phases = array.shape
    occ = generator.integers(0, occupancies, size=occupancies)
    path = generator.integers(0, paths, size=(occupancies, paths))
    phase = generator.integers(0, phases, size=(occupancies, paths, phases))
    return float(array[occ[:, None, None], path[:, :, None], phase].mean())


def cube(frame: pd.DataFrame) -> np.ndarray:
    pivot = frame.pivot(index="occupancy_idx", columns=["path_idx", "phase_idx"], values="effect_db").sort_index().sort_index(axis=1)
    occupancies = frame.occupancy_idx.nunique(); paths = frame.path_idx.nunique(); phases = frame.phase_idx.nunique()
    if pivot.shape != (occupancies, paths * phases) or pivot.isna().any().any(): raise RuntimeError("incomplete fixed-count hierarchy")
    return pivot.to_numpy(float).reshape(occupancies, paths, phases)


def main() -> None:
    raise SystemExit("BLOCKED LEGACY ROUTE: Stage 5C.2G-R fixed-count analysis is not authorized")
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/stage5c2gR/fixed_count.yaml")
    parser.add_argument("--protocol", default="configs/stage5c2gR/protocol.yaml")
    parser.add_argument("--results", default="results/stage5c2gR/fixed_count")
    parser.add_argument("--out", default="results/stage5c2gR/fixed_count_analysis")
    args = parser.parse_args()
    lock = assert_protocol_locked(protocol_path=args.protocol)
    raw = load_yaml(args.config); stage = raw["stage5c2gR_fixed_count"]; inference = stage["inference"]
    root = ROOT / args.results / lock["candidate_sha256"][:16]
    counts = [int(value) for value in stage["fixed_hole_counts"]]
    target_times = sorted(set(float(stage["fixed_time"]) + float(offset) for offset in stage["local_window_offsets"]))
    cells: dict[tuple[int, float], np.ndarray] = {}; rows = []; occupancy_rows = []
    for count in counts:
        count_root = root / f"holes_{count:02d}"
        manifest = json.loads((count_root / "stage5c2gR_fixed_count_manifest.json").read_text(encoding="utf-8"))
        if manifest.get("status") != "COMPLETE" or manifest.get("protocol_candidate_sha256") != lock["candidate_sha256"]: raise RuntimeError(f"incomplete count manifest: {count}")
        curves = pd.read_csv(count_root / "stage5c2gR_fixed_count_curves_all.csv")
        available = np.sort(curves.time.unique())
        for target in target_times:
            actual = float(available[np.argmin(np.abs(available - target))])
            paired = effects(curves[np.isclose(curves.time, actual)])
            cells[(count, target)] = cube(paired)
            rows.append({"hole_count": count, "target_time": target, "actual_time": actual, "mean_effect_db": float(paired.effect_db.mean())})
        fixed_actual = float(available[np.argmin(np.abs(available - float(stage["fixed_time"])))])
        fixed = effects(curves[np.isclose(curves.time, fixed_actual)])
        occupancy = fixed.groupby(["hole_count", "occupancy_idx", "occupancy_realization_id"], as_index=False).effect_db.mean().rename(columns={"effect_db": "occupancy_mean_effect_db"})
        descriptors = curves[(curves.label == "mobile_plus_spin_density") & np.isclose(curves.time, fixed_actual)].groupby("occupancy_realization_id", as_index=False).first()
        descriptor_columns = [column for column in descriptors if column.startswith("initial_")]
        occupancy_rows.append(occupancy.merge(descriptors[["occupancy_realization_id", *descriptor_columns]], on="occupancy_realization_id", how="left"))

    summary = pd.DataFrame(rows)
    generator = np.random.default_rng(int(inference["bootstrap_seed"])); draws = []
    for _ in range(int(inference["bootstrap_replicates"])):
        draws.append({key: draw_nested(value, generator) for key, value in cells.items()})
    centered_max = []
    point = {key: float(value.mean()) for key, value in cells.items()}
    for draw in draws: centered_max.append(max(abs(draw[key] - point[key]) for key in point))
    critical = float(np.quantile(centered_max, 1.0 - float(inference["familywise_alpha"])))
    summary["simultaneous_ci_low"] = summary.apply(lambda row: row.mean_effect_db - critical, axis=1)
    summary["simultaneous_ci_high"] = summary.apply(lambda row: row.mean_effect_db + critical, axis=1)
    delta = float(inference["smallest_effect_of_scientific_interest_db"])
    summary["practically_negative"] = summary.simultaneous_ci_high < -delta
    fixed_rows = summary[np.isclose(summary.target_time, float(stage["fixed_time"]))]
    passing_counts = fixed_rows[fixed_rows.practically_negative].hole_count.astype(int).tolist()
    central = int(inference["central_hole_count"])
    central_local = summary[summary.hole_count == central]
    gate = {"stage": "stage5c2gR_fixed_hole_confound_gate", "protocol_candidate_sha256": lock["candidate_sha256"], "smallest_effect_of_scientific_interest_db": delta, "simultaneous_critical_deviation_db": critical, "passing_counts": passing_counts, "required_counts_including_central_pass": bool(len(passing_counts) >= int(inference["required_counts"]) and central in passing_counts), "central_nearby_times_pass": bool(central_local.practically_negative.all()), "topology_confirmatory": False, "topology_scope": stage["topology_scope"]["description"]}
    gate["passed"] = bool(gate["required_counts_including_central_pass"] and gate["central_nearby_times_pass"])
    output = ROOT / args.out; output.mkdir(parents=True, exist_ok=True)
    summary.to_csv(output / "simultaneous_fixed_count_intervals.csv", index=False)
    pd.concat(occupancy_rows, ignore_index=True).to_csv(output / "exploratory_within_count_topology.csv", index=False)
    (output / "stage5c2gR_fixed_count_gate.json").write_text(json.dumps(gate, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(gate, indent=2))
    if not gate["passed"]: raise SystemExit("fixed-hole practical-effect gate failed; G5 remains blocked")


if __name__ == "__main__":
    main()
