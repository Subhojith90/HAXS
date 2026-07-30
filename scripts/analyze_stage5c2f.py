#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from haxs.validation.random_effects import balanced_random_effects_anova
from stage2_common import load_raw_config


UNIT_KEYS = ["occupancy_realization_id", "path_realization_id", "phase_realization_id"]


def balanced_nested_bootstrap_ci(frame: pd.DataFrame, n_boot: int, seed: int, ci: float = 0.95) -> tuple[float, float]:
    """Vectorized equivalent of the occupancy/path/phase nested resampler."""
    occupancies = sorted(frame.occupancy_idx.unique())
    paths = sorted(frame.path_idx.unique())
    phases = sorted(frame.phase_idx.unique())
    array = np.empty((len(occupancies), len(paths), len(phases)), dtype=float)
    for ii, occupancy in enumerate(occupancies):
        for jj, path in enumerate(paths):
            values = frame[(frame.occupancy_idx == occupancy) & (frame.path_idx == path)].sort_values("phase_idx").effect_db.to_numpy(float)
            if len(values) != len(phases):
                raise ValueError("nested bootstrap requires the complete preregistered balanced grid")
            array[ii, jj, :] = values
    rng = np.random.default_rng(int(seed))
    replicas = []
    remaining = int(n_boot)
    while remaining:
        batch = min(256, remaining)
        occ_draw = rng.integers(0, len(occupancies), size=(batch, len(occupancies)))
        path_draw = rng.integers(0, len(paths), size=(batch, len(occupancies), len(paths)))
        phase_draw = rng.integers(0, len(phases), size=(batch, len(occupancies), len(paths), len(phases)))
        sampled = array[occ_draw[:, :, None, None], path_draw[:, :, :, None], phase_draw]
        replicas.extend(sampled.mean(axis=(1, 2, 3)).tolist())
        remaining -= batch
    alpha = (1.0 - float(ci)) / 2.0
    return float(np.quantile(replicas, alpha)), float(np.quantile(replicas, 1.0 - alpha))


def normalize_units(frame: pd.DataFrame, confirmation: bool = False) -> pd.DataFrame:
    out = frame.copy()
    if confirmation:
        out["occupancy_realization_id"] = "confirmation_occ_" + out["occupancy_hash"].astype(str)
        # The static label has no mobile trajectory, so its simulator path hash
        # is intentionally constant across nominal paths. Pair the frozen block
        # using physical occupancy identity plus its recorded nested path index.
        out["path_realization_id"] = "confirmation_path_" + out["occupancy_hash"].astype(str) + "_" + out["path_idx"].astype(str)
        out["phase_realization_id"] = out["path_realization_id"] + "_phase_" + out["phase_idx"].astype(str)
    missing = [key for key in UNIT_KEYS if key not in out.columns]
    if missing:
        raise ValueError(f"missing immutable hierarchy keys: {missing}")
    return out


def paired_effects(finals: pd.DataFrame, metric: str = "xi2_db_fixed") -> pd.DataFrame:
    key_cols = UNIT_KEYS + ["occupancy_idx", "path_idx", "phase_idx", "occupancy_hash"]
    left = finals[finals.label == "static_only"][key_cols + [metric]].rename(columns={metric: "static"})
    right = finals[finals.label == "mobile_plus_spin_density"][UNIT_KEYS + [metric]].rename(columns={metric: "mobile_sd"})
    paired = left.merge(right, on=UNIT_KEYS, validate="one_to_one")
    paired["effect_db"] = paired["static"] - paired["mobile_sd"]
    return paired


def block_metrics(finals: pd.DataFrame, st: dict, block: str) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    effects = paired_effects(finals)
    anova = balanced_random_effects_anova(effects)
    low, high = balanced_nested_bootstrap_ci(
        effects, n_boot=int(st["bootstrap_samples"]),
        seed=int(st["bootstrap_seed"]) + (0 if block == "primary" else 1), ci=0.95,
    )
    occupancy = effects.groupby(["occupancy_idx", "occupancy_realization_id", "occupancy_hash"], as_index=False).effect_db.mean()
    occupancy = occupancy.rename(columns={"effect_db": "occupancy_mean_effect_db"})
    gates = st["gates"]
    row = {
        **anova, "block": block, "hierarchical_ci_low": low, "hierarchical_ci_high": high,
        "occupancy_negative_fraction": float((occupancy.occupancy_mean_effect_db < 0).mean()),
    }
    row["fixed_time_mean_pass"] = bool(row["mean_effect_db"] < float(gates["fixed_time_mean_below"]))
    row["fixed_time_ci_pass"] = bool(high < float(gates["hierarchical_ci_high_below"]))
    row["absolute_mc_se_pass"] = bool(row["hierarchical_standard_error"] <= float(gates["absolute_mc_se_at_most"]))
    row["occupancy_negative_fraction_pass"] = bool(row["occupancy_negative_fraction"] >= float(gates["occupancy_negative_fraction_at_least"]))
    return row, effects, occupancy


def local_window(curves: pd.DataFrame, st: dict, block: str) -> pd.DataFrame:
    fixed_time = float(curves["time"].drop_duplicates().sort_values().iloc[int(round(float(st["fixed_time_fraction"]) * (curves.time.nunique() - 1)))])
    available = np.sort(curves.time.unique())
    rows = []
    for offset in st["local_window_offsets"]:
        actual = float(available[np.argmin(np.abs(available - (fixed_time + float(offset))))])
        sub = curves[np.isclose(curves.time, actual)]
        effects = paired_effects(sub, metric="xi2_db")
        low, high = balanced_nested_bootstrap_ci(effects, n_boot=int(st["bootstrap_samples"]), seed=int(st["bootstrap_seed"]) + 100 + len(rows), ci=0.95)
        rows.append({"block": block, "offset": float(offset), "actual_time": actual, "mean_effect_db": float(effects.effect_db.mean()), "hierarchical_ci_low": low, "hierarchical_ci_high": high, "negative": bool(high < 0)})
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/stage5c2f/primary_lock.yaml")
    ap.add_argument("--primary", default="results/stage5c2f/primary")
    ap.add_argument("--confirmation")
    ap.add_argument("--out", default="results/stage5c2f/analysis")
    args = ap.parse_args()
    raw = load_raw_config(args.config)
    st = raw["stage5c2f"]
    primary_path = ROOT / args.primary
    confirmation_path = ROOT / (args.confirmation or st["locked_confirmation"])
    primary_finals = normalize_units(pd.read_csv(primary_path / "stage5c2f_finals.csv"))
    primary_curves = normalize_units(pd.read_csv(primary_path / "stage5c2f_curves_all.csv"))
    confirmation_finals = normalize_units(pd.read_csv(confirmation_path / "stage5c2d_finals.csv"), confirmation=True)
    confirmation_curves = normalize_units(pd.read_csv(confirmation_path / "stage5c2d_curves_all.csv"), confirmation=True)

    primary_row, primary_effects, primary_occ = block_metrics(primary_finals, st, "primary")
    confirmation_row, confirmation_effects, confirmation_occ = block_metrics(confirmation_finals, st, "confirmation")
    local = pd.concat([local_window(primary_curves, st, "primary"), local_window(confirmation_curves, st, "confirmation")], ignore_index=True)
    primary_row["local_window_all_negative"] = bool(local[local.block == "primary"].negative.all())
    confirmation_row["local_window_all_negative"] = bool(local[local.block == "confirmation"].negative.all())

    p = primary_occ.occupancy_mean_effect_db.to_numpy(float)
    c = confirmation_occ.occupancy_mean_effect_db.to_numpy(float)
    difference = float(np.mean(p) - np.mean(c))
    se = float(np.sqrt(np.var(p, ddof=1) / len(p) + np.var(c, ddof=1) / len(c)))
    numerator = (np.var(p, ddof=1) / len(p) + np.var(c, ddof=1) / len(c)) ** 2
    denominator = ((np.var(p, ddof=1) / len(p)) ** 2 / (len(p) - 1)) + ((np.var(c, ddof=1) / len(c)) ** 2 / (len(c) - 1))
    dof = float(numerator / denominator)
    critical = float(scipy_stats.t.ppf(0.95, dof))
    eq_low, eq_high = difference - critical * se, difference + critical * se
    margin = float(st["gates"]["equivalence_margin_db"])
    equivalence_pass = bool(eq_low >= -margin and eq_high <= margin)
    for row in (primary_row, confirmation_row):
        row.update({"equivalence_difference_db": difference, "equivalence_90_low": eq_low, "equivalence_90_high": eq_high, "equivalence_pass": equivalence_pass})

    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([primary_row, confirmation_row]).to_csv(out / "stage5c2f_gate_table.csv", index=False)
    local.to_csv(out / "stage5c2f_local_window_table.csv", index=False)
    pd.concat([primary_effects.assign(block="primary"), confirmation_effects.assign(block="confirmation")], ignore_index=True).to_csv(out / "stage5c2f_paired_effects.csv", index=False)
    pd.concat([primary_occ.assign(block="primary"), confirmation_occ.assign(block="confirmation")], ignore_index=True).to_csv(out / "stage5c2f_occupancy_effects.csv", index=False)
    summary = {"stage": "stage5c2f_analysis", "estimator": st["estimator"], "equivalence_method": st["equivalence_method"], "claim_scope": st["claim_scope"]}
    (out / "stage5c2f_analysis_metadata.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
