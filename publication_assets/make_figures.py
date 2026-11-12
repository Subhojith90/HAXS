#!/usr/bin/env python3
"""Generate publication figures from the frozen Stage 5C.2F evidence."""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA, RAW, OUT = ROOT / "source_data", ROOT / "source_data" / "raw", ROOT / "figures"
OUT.mkdir(exist_ok=True)

BLUE, ORANGE, GREEN, PURPLE, GREY = "#176B87", "#D55E00", "#2A9D8F", "#7353BA", "#52606D"
COLORS = {"primary": BLUE, "confirmation": ORANGE}
LABELS = {"static_only": "Static occupancy", "mobile_plus_spin_density": "Moving occupancy + local field"}


def save(fig: plt.Figure, stem: str) -> None:
    fig.savefig(OUT / f"{stem}.pdf", bbox_inches="tight")
    fig.savefig(OUT / f"{stem}.png", dpi=360, bbox_inches="tight")
    plt.close(fig)


def style(ax: plt.Axes, grid: str = "y") -> None:
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis=grid, color="#DDE3E8", lw=0.7, zorder=0)


def model_workflow_figure() -> None:
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ax.set(xlim=(0, 10), ylim=(0, 6)); ax.axis("off")
    holes = {(0, 1, 2), (1, 0, 1), (2, 2, 0), (2, 0, 2)}
    for z in range(3):
        x0, y0 = 0.55 + 0.38*z, 2.05 + 0.5*z
        for x in range(3):
            for y in range(3):
                xx, yy = x0 + 0.48*x, y0 + 0.48*y
                ax.scatter(xx, yy, s=86, facecolor="white" if (z, x, y) in holes else BLUE,
                           edgecolor=GREY, linewidth=1.0, zorder=3)
        ax.add_patch(FancyBboxPatch((x0-0.22, y0-0.22), 1.4, 1.4, boxstyle="round,pad=0.04",
                                    fill=False, edgecolor="#9AA5B1", linewidth=0.8))
    ax.text(1.35, 4.65, r"open $3\times3\times3$ lattice", ha="center", fontsize=10, weight="bold")
    ax.text(1.35, 1.35, r"Bernoulli holes: $p_h=0.18$", ha="center", fontsize=9)
    boxes = [
        (3.25, 3.7, 2.0, 1.25, "STATIC", "fixed occupancy\n" + r"$\eta=\lambda_{\rm sd}=0$", BLUE),
        (3.25, 1.55, 2.0, 1.45, "MOVING + FIELD", "exclusion walk, " + r"$\eta=0.55$" + "\n" + r"$h_i^z=\lambda_{\rm sd}\sum_j(1-n_j)$", ORANGE),
        (6.25, 2.55, 2.8, 1.45, "PAIRED ENDPOINT", r"$J_\perp t=0.9227$"+"\n"+r"$\Delta=\xi^2_{\rm static,dB}-\xi^2_{\rm mov,dB}$", PURPLE),
    ]
    for x, y, w, h, title, subtitle, color in boxes:
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.12",
                                    facecolor=color+"18", edgecolor=color, linewidth=1.4))
        ax.text(x+w/2, y+h*0.68, title, ha="center", va="center", fontsize=9.5, weight="bold", color=color)
        ax.text(x+w/2, y+h*0.31, subtitle, ha="center", va="center", fontsize=8.6)
    for y in (4.32, 2.27):
        ax.add_patch(FancyArrowPatch((2.15, 3.22), (3.15, y), arrowstyle="-|>", mutation_scale=12,
                                     linewidth=1.1, color=GREY, connectionstyle="arc3,rad=0.08"))
    for start in ((5.27, 4.32), (5.27, 2.27)):
        ax.add_patch(FancyArrowPatch(start, (6.15, 3.27), arrowstyle="-|>", mutation_scale=12,
                                     linewidth=1.1, color=GREY))
    save(fig, "model_and_estimand")


def dynamics_figure() -> None:
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 6.2), sharex="col")
    for col, block in enumerate(("primary", "confirmation")):
        data = pd.read_csv(RAW / f"{block}_curves.csv")
        occ_abs = data.groupby(["occupancy_idx", "label", "time"], as_index=False).xi2_db.mean()
        summary = occ_abs.groupby(["label", "time"]).xi2_db.agg(
            mean="mean", q10=lambda x: np.quantile(x, .10), q90=lambda x: np.quantile(x, .90)).reset_index()
        for label, color in (("static_only", BLUE), ("mobile_plus_spin_density", ORANGE)):
            g = summary[summary.label == label]
            axes[0, col].plot(g.time, g["mean"], color=color, lw=1.8, label=LABELS[label])
            axes[0, col].fill_between(g.time, g.q10, g.q90, color=color, alpha=.14, linewidth=0)
        key = ["occupancy_idx", "path_idx", "phase_idx", "time"]
        paired = data.pivot(index=key, columns="label", values="xi2_db").reset_index()
        paired["effect"] = paired.static_only - paired.mobile_plus_spin_density
        occ = paired.groupby(["occupancy_idx", "time"], as_index=False).effect.mean()
        effect = occ.groupby("time").effect.agg(
            mean="mean", q10=lambda x: np.quantile(x, .10), q90=lambda x: np.quantile(x, .90)).reset_index()
        axes[1, col].plot(effect.time, effect["mean"], color=COLORS[block], lw=1.9)
        axes[1, col].fill_between(effect.time, effect.q10, effect.q90, color=COLORS[block], alpha=.18, linewidth=0)
        for row in range(2):
            axes[row, col].axvline(.9227272727, color="#6B7280", lw=1.0, ls=":"); style(axes[row, col])
        axes[0, col].set_title("Primary block" if block == "primary" else "Frozen confirmation")
        axes[1, col].axhline(0, color="#4B5563", lw=.9, ls="--")
        axes[1, col].set_xlabel(r"Dimensionless time $J_\perp t$")
    axes[0, 0].set_ylabel(r"Absolute $\xi^2_{\rm dB}$")
    axes[1, 0].set_ylabel(r"Paired contrast $\Delta$ (dB)")
    axes[0, 0].legend(frameon=False, fontsize=8, loc="lower left")
    axes[0, 1].legend(frameon=False, fontsize=8, loc="lower left")
    fig.text(.5, .985, "Absolute dynamics and paired contrast", ha="center", va="top", fontsize=11, weight="bold")
    fig.tight_layout(rect=(0, 0, 1, .965)); save(fig, "dynamics_and_contrast")


def occupancy_figure() -> None:
    effects = pd.read_csv(DATA / "stage5c2f_occupancy_effects.csv")
    gate = pd.read_csv(DATA / "stage5c2f_gate_table.csv").set_index("block")
    fig, ax = plt.subplots(figsize=(7.0, 3.7)); xmap = {"primary": 0., "confirmation": 1.}
    for block in ("primary", "confirmation"):
        values = effects.loc[effects.block == block, "occupancy_mean_effect_db"].to_numpy(float)
        ax.scatter(xmap[block]+np.linspace(-.17, .17, len(values)), values, s=31, color=COLORS[block],
                   alpha=.82, edgecolor="white", linewidth=.5, zorder=3)
        row = gate.loc[block]; mean, low, high = map(float, (row.mean_effect_db, row.hierarchical_ci_low, row.hierarchical_ci_high))
        ax.errorbar(xmap[block], mean, yerr=[[mean-low], [high-mean]], fmt="D", color="black",
                    mfc=COLORS[block], mec="black", capsize=5, lw=1.8, ms=7, zorder=4)
    ax.axhline(0, color="#444444", lw=1, ls="--"); ax.set(xlim=(-.45, 1.45), ylim=(-.82, .12))
    ax.set_xticks([0, 1], ["Primary\n(16 occupancies)", "Frozen confirmation\n(12 occupancies)"])
    ax.set_ylabel(r"$\Delta=\xi^2_{\rm static,dB}-\xi^2_{\rm mov,dB}$")
    ax.text(.98, .05, "moving condition lower", transform=ax.transAxes, ha="right", va="bottom", fontsize=8, color=GREY)
    ax.text(.98, .95, "static condition lower", transform=ax.transAxes, ha="right", va="top", fontsize=8, color=GREY)
    style(ax); fig.tight_layout(); save(fig, "occupancy_effects")


def time_window_figure() -> None:
    data = pd.read_csv(DATA / "stage5c2f_local_window_table.csv")
    fig, ax = plt.subplots(figsize=(7.0, 3.7))
    for block, marker in (("primary", "o"), ("confirmation", "s")):
        group = data[data.block == block].sort_values("actual_time")
        mean = group.mean_effect_db.to_numpy(float); low = group.hierarchical_ci_low.to_numpy(float); high = group.hierarchical_ci_high.to_numpy(float)
        ax.errorbar(group.actual_time, mean, yerr=np.vstack([mean-low, high-mean]), marker=marker, ms=6,
                    lw=1.7, capsize=4, color=COLORS[block], label="Primary" if block == "primary" else "Frozen confirmation")
    ax.axhline(0, color="#444444", lw=1, ls="--"); ax.axvline(.9227272727, color="#777777", lw=1, ls=":")
    ax.set_xlabel(r"Dimensionless time $J_\perp t$"); ax.set_ylabel(r"Paired contrast $\Delta$ (dB)")
    ax.legend(frameon=False, loc="lower left"); style(ax); fig.tight_layout(); save(fig, "local_time_window")


def variance_figure() -> None:
    data = pd.read_csv(DATA / "variance_decomposition.csv"); blocks = ["primary", "confirmation"]
    fig, ax = plt.subplots(figsize=(7.0, 3.3)); left = np.zeros(2)
    for component, color in zip(["occupancy", "hole path", "phase batch"], [BLUE, ORANGE, GREEN]):
        vals = np.array([data[(data.block == b) & (data.component == component)].fraction.iloc[0] for b in blocks])
        ax.barh([0, 1], vals, left=left, color=color, label=component.title(), height=.54)
        for idx, (start, val) in enumerate(zip(left, vals)):
            if val > .07: ax.text(start+val/2, idx, f"{100*val:.1f}%", ha="center", va="center", color="white", fontsize=8.5)
        left += vals
    ax.set_xlim(0, 1); ax.set_yticks([0, 1], ["Primary", "Frozen confirmation"]); ax.invert_yaxis()
    ax.set_xlabel("Fraction of variance of the block mean"); ax.legend(frameon=False, ncol=3, loc="lower center", bbox_to_anchor=(.5, 1.01))
    style(ax, "x"); fig.tight_layout(); save(fig, "variance_decomposition")


def validation_figure() -> None:
    data = pd.read_csv(RAW / "ed_dtwa_curve.csv")
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.25))
    axes[0].plot(data.time, data.ed_xi2_db, color=BLUE, lw=1.9, label="Exact diagonalization")
    axes[0].plot(data.time, data.dtwa_xi2_db, color=ORANGE, lw=1.6, ls="--", label="DTWA, 4096 trajectories")
    axes[0].set(xlabel=r"Dimensionless time $J_\perp t$", ylabel=r"$\xi^2_{\rm dB}$"); axes[0].legend(frameon=False, fontsize=8)
    axes[1].plot(data.time, np.abs(data.xi2_db_error), color=PURPLE, lw=1.8, label=r"$|\Delta\xi^2_{\rm dB}|$")
    axes[1].axhline(.15, color="#C0392B", lw=1.1, ls=":", label="RMSE gate threshold")
    axes[1].set(xlabel=r"Dimensionless time $J_\perp t$", ylabel="Absolute pointwise error (dB)"); axes[1].legend(frameon=False, fontsize=8)
    for ax in axes: style(ax)
    fig.tight_layout(); save(fig, "small_system_validation")


if __name__ == "__main__":
    plt.rcParams.update({"font.size": 9.5, "font.family": "DejaVu Sans", "pdf.fonttype": 42,
                         "ps.fonttype": 42, "axes.titleweight": "bold"})
    model_workflow_figure(); dynamics_figure(); occupancy_figure(); time_window_figure(); variance_figure(); validation_figure()
