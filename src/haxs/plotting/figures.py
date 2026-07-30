from __future__ import annotations
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from .styles import apply_style


def _save(fig, path):
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(p)
    plt.close(fig)
    return str(p)

def figure_model_hierarchy(path: str | Path):
    apply_style()
    fig, ax = plt.subplots(figsize=(8.5, 3.8))
    ax.axis("off")
    labels = ["Ideal\nXXZ", "Static\nholes", "Mobile-hole\nsurrogate", "Spin-density\nfield", "Controls", "Dual\ncertificate"]
    xs = np.linspace(0.08, 0.92, len(labels))
    y = 0.58
    for i, (x, lab) in enumerate(zip(xs, labels)):
        ax.text(x, y, lab, ha="center", va="center", fontsize=8,
                bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="black", lw=0.9),
                transform=ax.transAxes)
        if i < len(labels)-1:
            ax.annotate("", xy=(xs[i+1]-0.075, y), xytext=(x+0.075, y),
                        arrowprops=dict(arrowstyle="->", lw=0.8), xycoords=ax.transAxes)
    ax.text(0.5, 0.18, "Routes: constructive recovery | mechanism diagnostic | restricted no-go",
            ha="center", fontsize=9, transform=ax.transAxes)
    ax.set_title("HAXS model hierarchy and decision routes", fontsize=11)
    return _save(fig, path)

def figure_validation(validation_csv: str | Path, out: str | Path):
    apply_style(); df = pd.read_csv(validation_csv)
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    metrics = df["metric"].astype(str).to_list(); values = df["value"].astype(float).to_numpy()
    plot_values = np.where(np.isfinite(values), np.abs(values), np.nan)
    ax.bar(np.arange(len(metrics)), plot_values)
    ax.set_yscale("log")
    ax.set_xticks(np.arange(len(metrics))); ax.set_xticklabels(metrics, rotation=35, ha="right")
    ax.set_ylabel("absolute value (log scale)"); ax.set_title("Validation and sanity metrics")
    return _save(fig, out)

def figure_mechanism(curves_csv: str | Path, out: str | Path):
    apply_style(); df = pd.read_csv(curves_csv)
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    for label, g in df.groupby("label"):
        ax.plot(g["time"], g["xi2_db"], label=label)
    ax.axhline(0.0, linestyle="--")
    ax.set_xlabel("time [1/J_perp]"); ax.set_ylabel("xi2 dB = 10 log10 xi2")
    ax.set_title("Mechanism decomposition: squeezing curves")
    ax.legend(fontsize=7)
    return _save(fig, out)

def figure_inverse_design(summary_csv: str | Path, out: str | Path):
    apply_style(); df = pd.read_csv(summary_csv)
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    labels = df["label"].astype(str); vals = df["mean_xi2_db"].astype(float)
    ax.bar(labels, vals); ax.axhline(0.0, linestyle="--")
    ax.set_ylabel("best mean xi2 dB"); ax.set_title("Baseline vs inverse-designed control (paper-lite)")
    return _save(fig, out)

def figure_threshold(threshold_csv: str | Path, out: str | Path):
    apply_style(); df = pd.read_csv(threshold_csv)
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    for (d, eta, lsd), g in df.groupby(["dimension", "mobile_eta", "lambda_sd"]):
        lbl = f"d={d}, eta={eta}, lsd={lsd}"
        gg = g.sort_values("p_h")
        ax.errorbar(gg["p_h"], gg["xi2_db_min_mean"], yerr=gg["xi2_db_min_std"], marker="o", label=lbl)
    ax.axhline(float(df["target_xi2_db"].iloc[0]), linestyle="--")
    ax.set_xlabel("hole fraction p_h"); ax.set_ylabel("min xi2 dB")
    ax.set_title("Restricted empirical threshold scan")
    ax.legend(fontsize=6)
    return _save(fig, out)

def figure_decision(decision_json: str | Path, out: str | Path):
    apply_style(); decision = json.loads(Path(decision_json).read_text())
    scores = decision.get("route_scores", {})
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    labels = list(scores.keys()) or ["constructive", "mechanism", "nogo"]
    vals = [float(scores.get(k, 0.0)) for k in labels]
    ax.bar(labels, vals); ax.set_ylim(0, 1.05); ax.set_ylabel("route score")
    ax.set_title("Kill/no-kill decision: " + str(decision.get("status", "unknown")))
    ax.text(0.5, -0.18, str(decision.get("reason", "")), transform=ax.transAxes, ha="center", va="top")
    return _save(fig, out)
