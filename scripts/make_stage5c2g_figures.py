#!/usr/bin/env python
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", default="results/stage5c2g")
    parser.add_argument("--out", default="figures/stage5c2g")
    args = parser.parse_args()
    root, output = ROOT / args.results, ROOT / args.out
    output.mkdir(parents=True, exist_ok=True)
    fixed = pd.read_csv(root / "fixed_count_analysis/stage5c2g_fixed_count_summary.csv")
    sensitivity = pd.read_csv(root / "fixed_count_analysis/stage5c2g_estimator_sensitivity.csv")
    topology = pd.read_csv(root / "fixed_count_analysis/stage5c2g_occupancy_topology_table.csv")
    comparisons = pd.read_csv(root / "validity_analysis/stage5c2g_time_profile_comparison.csv")
    contrasts = pd.read_csv(root / "validity_analysis/stage5c2g_component_contrasts.csv")
    exact = pd.read_csv(root / "validation/stage5c2g_exact_curves.csv")
    surrogate = pd.read_csv(root / "validation/stage5c2g_surrogate_curves.csv")

    fig, axis = plt.subplots(figsize=(6.2, 4.0))
    axis.errorbar(fixed.hole_count, fixed.mean_effect_db, yerr=[fixed.mean_effect_db - fixed.primary_ci_low, fixed.primary_ci_high - fixed.mean_effect_db], fmt="o", capsize=4)
    axis.axhline(0.0, color="black", linewidth=1); axis.set(xlabel="Fixed hole count", ylabel="Static - combined effect (dB)")
    fig.tight_layout(); fig.savefig(output / "fixed_hole_count_intervals.png", dpi=180); plt.close(fig)

    fig, axis = plt.subplots(figsize=(7.2, 4.2))
    estimators = list(sensitivity.estimator.unique())
    for offset, estimator in enumerate(estimators):
        subset = sensitivity[sensitivity.estimator == estimator]
        x = subset.hole_count + (offset - (len(estimators) - 1) / 2) * 0.12
        center = (subset.ci_low + subset.ci_high) / 2
        axis.errorbar(x, center, yerr=[center - subset.ci_low, subset.ci_high - center], fmt="o", capsize=3, label=estimator)
    axis.axhline(0.0, color="black", linewidth=1); axis.legend(fontsize=7); axis.set(xlabel="Fixed hole count", ylabel="95% interval (dB)")
    fig.tight_layout(); fig.savefig(output / "estimator_sensitivity.png", dpi=180); plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.8))
    axes[0].scatter(topology.initial_active_bonds, topology.occupancy_mean_effect_db, c=topology.hole_count)
    axes[0].set(xlabel="Initial active bonds", ylabel="Occupancy mean effect (dB)")
    axes[1].scatter(topology.initial_hole_clustering_fraction, topology.occupancy_mean_effect_db, c=topology.hole_count)
    axes[1].set(xlabel="Hole clustering fraction", ylabel="Occupancy mean effect (dB)")
    fig.tight_layout(); fig.savefig(output / "topology_moderation_exploratory.png", dpi=180); plt.close(fig)

    case_ids = list(exact.case_id.unique())
    fig, axes = plt.subplots(len(case_ids), 1, figsize=(7.0, 2.7 * len(case_ids)), squeeze=False)
    for axis, case_id in zip(axes[:, 0], case_ids):
        for label in ["static_only", "mobile_only", "spin_density_only", "combined"]:
            exact_line = exact[(exact.case_id == case_id) & (exact.label == label)]
            surrogate_line = surrogate[(surrogate.case_id == case_id) & (surrogate.label == label)]
            axis.plot(exact_line.time, exact_line.xi2_db, label=f"exact {label}")
            axis.plot(surrogate_line.time, surrogate_line.xi2_db, linestyle="--", label=f"surrogate {label}")
        axis.set_title(case_id); axis.set_ylabel("xi2 (dB)")
    axes[-1, 0].set_xlabel("time"); axes[0, 0].legend(ncol=2, fontsize=6)
    fig.tight_layout(); fig.savefig(output / "exact_surrogate_time_profiles.png", dpi=180); plt.close(fig)

    fig, axis = plt.subplots(figsize=(5.0, 5.0))
    axis.scatter(contrasts.exact_effect_db, contrasts.surrogate_effect_db)
    limits = [float(min(contrasts.exact_effect_db.min(), contrasts.surrogate_effect_db.min())), float(max(contrasts.exact_effect_db.max(), contrasts.surrogate_effect_db.max()))]
    axis.plot(limits, limits, color="black", linewidth=1); axis.set(xlabel="Exact contrast (dB)", ylabel="Surrogate contrast (dB)")
    fig.tight_layout(); fig.savefig(output / "exact_vs_surrogate_contrasts.png", dpi=180); plt.close(fig)


if __name__ == "__main__":
    main()

