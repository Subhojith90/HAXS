#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--analysis", default="results/stage5c2f/analysis")
    args = ap.parse_args()
    analysis = ROOT / args.analysis
    decision = json.loads((analysis / "stage5c2f_decision.json").read_text(encoding="utf-8"))
    gates = pd.read_csv(analysis / "stage5c2f_gate_table.csv")
    selected = ["block", "mean_effect_db", "hierarchical_standard_error", "hierarchical_ci_low", "hierarchical_ci_high", "occupancy_negative_fraction", "local_window_all_negative", "equivalence_pass"]
    header = "| " + " | ".join(selected) + " |"
    separator = "| " + " | ".join(["---"] * len(selected)) + " |"
    rows = ["| " + " | ".join(str(row[column]) for column in selected) + " |" for _, row in gates.iterrows()]
    lines = ["# Stage 5C.2F source-generated report", "", f"Decision: **{decision['decision']}**", "", "The confirmation block remained frozen. Stage 5C3 production, Stage 5D, public release, and publication claims remain blocked pending supervisor review.", "", "## Gate table", "", header, separator, *rows, "", "## Decision reasons", ""]
    lines.extend(f"- {reason}" for reason in decision["reasons"])
    lines.append("")
    (analysis / "STAGE5C2F_REPORT.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
