#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from haxs.validation.random_effects import balanced_random_effects_anova
from stage5c2g_common import assert_protocol_locked, load_yaml

UNIT_KEYS = ["hole_count", "occupancy_realization_id", "path_realization_id", "phase_realization_id"]


def paired_effects(frame: pd.DataFrame, metric: str) -> pd.DataFrame:
    metadata = UNIT_KEYS + ["occupancy_idx", "path_idx", "phase_idx", "occupancy_hash"]
    static = frame[frame.label == "static_only"][metadata + [metric]].rename(columns={metric: "static"})
    combined = frame[frame.label == "mobile_plus_spin_density"][UNIT_KEYS + [metric]].rename(columns={metric: "combined"})
    paired = static.merge(combined, on=UNIT_KEYS, validate="one_to_one")
    paired["effect_db"] = paired.static - paired.combined
    return paired


def nested_bootstrap(frame: pd.DataFrame, replicates: int, seed: int) -> tuple[float, float, float, float]:
    occupancies = sorted(frame.occupancy_idx.unique())
    paths = sorted(frame.path_idx.unique())
    phases = sorted(frame.phase_idx.unique())
    array = np.empty((len(occupancies), len(paths), len(phases)), dtype=float)
    for oi, occupancy in enumerate(occupancies):
        for pj, path in enumerate(paths):
            values = frame[(frame.occupancy_idx == occupancy) & (frame.path_idx == path)].sort_values("phase_idx").effect_db.to_numpy(float)
            if len(values) != len(phases):
                raise ValueError("fixed-count analysis requires a complete balanced occupancy/path/phase grid")
            array[oi, pj] = values
    generator = np.random.default_rng(int(seed))
    samples = []
    remaining = int(replicates)
    while remaining:
        batch = min(256, remaining)
        occ_draw = generator.integers(0, len(occupancies), size=(batch, len(occupancies)))
        path_draw = generator.integers(0, len(paths), size=(batch, len(occupancies), len(paths)))
        phase_draw = generator.integers(0, len(phases), size=(batch, len(occupancies), len(paths), len(phases)))
        selected = array[occ_draw[:, :, None, None], path_draw[:, :, :, None], phase_draw]
        samples.extend(selected.mean(axis=(1, 2, 3)).tolist())
        remaining -= batch
    values = np.asarray(samples, dtype=float)
    return float(array.mean()), float(values.std(ddof=1)), float(np.quantile(values, 0.025)), float(np.quantile(values, 0.975))


def occupancy_t_interval(frame: pd.DataFrame) -> tuple[float, float, float]:
    means = frame.groupby("occupancy_realization_id").effect_db.mean().to_numpy(float)
    standard_error = float(stats.sem(means))
    critical = float(stats.t.ppf(0.975, len(means) - 1))
    return standard_error, float(means.mean() - critical * standard_error), float(means.mean() + critical * standard_error)


def topology_regression(occupancy_table: pd.DataFrame) -> pd.DataFrame:
    columns = ["initial_active_bonds", "initial_largest_connected_component_fraction", "initial_occupied_degree_variance", "initial_hole_clustering_fraction", "initial_boundary_hole_fraction"]
    available = [column for column in columns if column in occupancy_table.columns]
    if not available:
        return pd.DataFrame([{"term": "unavailable", "coefficient": np.nan, "exploratory": True}])
    design = occupancy_table[available].astype(float)
    scale = design.std(ddof=0).replace(0.0, 1.0)
    standardized = (design - design.mean()) / scale
    matrix = np.column_stack([np.ones(len(standardized)), standardized.to_numpy(float)])
    response = occupancy_table.occupancy_mean_effect_db.to_numpy(float)
    coefficients, *_ = np.linalg.lstsq(matrix, response, rcond=None)
    return pd.DataFrame({"term": ["intercept", *available], "coefficient": coefficients, "exploratory": True})


def main() -> None:
    raise SystemExit("REJECTED LEGACY ROUTE: Stage 5C.2G fixed-count analysis is disabled")
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/stage5c2g/fixed_count.yaml")
    parser.add_argument("--results", default="results/stage5c2g/fixed_count")
    parser.add_argument("--out", default="results/stage5c2g/fixed_count_analysis")
    args = parser.parse_args()
    assert_protocol_locked()
    raw = load_yaml(args.config)
    stage = raw["stage5c2g_fixed_count"]
    root = ROOT / args.results
    output = ROOT / args.out
    output.mkdir(parents=True, exist_ok=True)
    summaries, sensitivity, local_rows, occupancy_rows = [], [], [], []

    for count in [int(value) for value in stage["fixed_hole_counts"]]:
        count_root = root / f"holes_{count:02d}"
        finals = pd.read_csv(count_root / "stage5c2g_fixed_count_finals.csv")
        curves = pd.read_csv(count_root / "stage5c2g_fixed_count_curves_all.csv")
        effects = paired_effects(finals, "xi2_db_fixed")
        mean, bootstrap_se, bootstrap_low, bootstrap_high = nested_bootstrap(effects, int(stage["primary_bootstrap_replicates"]), int(stage["primary_bootstrap_seed"]) + count)
        anova = balanced_random_effects_anova(effects)
        anova_low = float(mean - 1.96 * anova["hierarchical_standard_error"])
        anova_high = float(mean + 1.96 * anova["hierarchical_standard_error"])
        t_se, t_low, t_high = occupancy_t_interval(effects)
        conclusion = bootstrap_high < 0.0
        sensitivity_agrees = bool((anova_high < 0.0) == conclusion and (t_high < 0.0) == conclusion)
        summaries.append({"hole_count": count, "mean_effect_db": mean, "primary_bootstrap_se": bootstrap_se, "primary_ci_low": bootstrap_low, "primary_ci_high": bootstrap_high, "primary_negative": conclusion, "estimator_conclusion_agreement": sensitivity_agrees, **anova})
        sensitivity.extend([
            {"hole_count": count, "estimator": "nested_cluster_bootstrap_20000", "standard_error": bootstrap_se, "ci_low": bootstrap_low, "ci_high": bootstrap_high, "negative": conclusion},
            {"hole_count": count, "estimator": "balanced_random_effects_anova_normal", "standard_error": anova["hierarchical_standard_error"], "ci_low": anova_low, "ci_high": anova_high, "negative": anova_high < 0.0},
            {"hole_count": count, "estimator": "equal_occupancy_t", "standard_error": t_se, "ci_low": t_low, "ci_high": t_high, "negative": t_high < 0.0},
        ])
        combined_metadata = finals[finals.label == "mobile_plus_spin_density"].groupby("occupancy_realization_id", as_index=False).first()
        occupancy = effects.groupby(["hole_count", "occupancy_idx", "occupancy_realization_id", "occupancy_hash"], as_index=False).effect_db.mean().rename(columns={"effect_db": "occupancy_mean_effect_db"})
        descriptor_columns = [column for column in combined_metadata.columns if column.startswith("initial_")]
        occupancy = occupancy.merge(combined_metadata[["occupancy_realization_id", *descriptor_columns]].drop_duplicates("occupancy_realization_id"), on="occupancy_realization_id", how="left")
        occupancy_rows.append(occupancy)
        available_times = np.sort(curves.time.unique())
        for offset_index, offset in enumerate(stage["local_window_offsets"]):
            actual = float(available_times[np.argmin(np.abs(available_times - (float(stage["fixed_time"]) + float(offset))))])
            local_effects = paired_effects(curves[np.isclose(curves.time, actual)], "xi2_db")
            local_mean, local_se, low, high = nested_bootstrap(local_effects, int(stage["primary_bootstrap_replicates"]), int(stage["primary_bootstrap_seed"]) + 1000 + count * 10 + offset_index)
            local_rows.append({"hole_count": count, "offset": float(offset), "actual_time": actual, "mean_effect_db": local_mean, "bootstrap_se": local_se, "ci_low": low, "ci_high": high, "negative": high < 0.0})

    summary = pd.DataFrame(summaries)
    sensitivity_table = pd.DataFrame(sensitivity)
    local_table = pd.DataFrame(local_rows)
    occupancy_table = pd.concat(occupancy_rows, ignore_index=True)
    central = int(stage["gates"]["central_hole_count"])
    central_connected = occupancy_table[(occupancy_table.hole_count == central) & occupancy_table.initial_occupied_graph_connected.astype(bool)]
    minimum_connected = int(stage["gates"]["minimum_connected_occupancies_for_subset_gate"])
    if len(central_connected) >= minimum_connected:
        connected_values = central_connected.occupancy_mean_effect_db.to_numpy(float)
        connected_se = float(stats.sem(connected_values))
        connected_high = float(connected_values.mean() + stats.t.ppf(0.975, len(connected_values) - 1) * connected_se)
    else:
        connected_high = float("nan")
    negative_counts = summary[summary.primary_negative].hole_count.astype(int).tolist()
    gate = {
        "stage": "stage5c2g_fixed_count_gate",
        "negative_counts": negative_counts,
        "at_least_two_counts_including_central": bool(len(negative_counts) >= int(stage["gates"]["required_negative_counts"]) and central in negative_counts),
        "central_connected_subset_n": int(len(central_connected)),
        "central_connected_subset_ci_high": connected_high,
        "central_connected_subset_negative": bool(np.isfinite(connected_high) and connected_high < 0.0),
        "central_local_window_all_negative": bool(local_table[local_table.hole_count == central].negative.all()),
        "estimator_sensitivity_agrees": bool(summary.estimator_conclusion_agreement.all()),
    }
    gate["passed"] = bool(gate["at_least_two_counts_including_central"] and gate["central_connected_subset_negative"] and gate["central_local_window_all_negative"] and gate["estimator_sensitivity_agrees"])
    summary.to_csv(output / "stage5c2g_fixed_count_summary.csv", index=False)
    sensitivity_table.to_csv(output / "stage5c2g_estimator_sensitivity.csv", index=False)
    local_table.to_csv(output / "stage5c2g_fixed_count_local_window.csv", index=False)
    occupancy_table.to_csv(output / "stage5c2g_occupancy_topology_table.csv", index=False)
    topology_regression(occupancy_table).to_csv(output / "stage5c2g_topology_coefficients_exploratory.csv", index=False)
    (output / "stage5c2g_fixed_count_gate.json").write_text(json.dumps(gate, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(gate, indent=2))


if __name__ == "__main__":
    main()
