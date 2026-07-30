#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def markdown_table(frame: pd.DataFrame) -> list[str]:
    columns = list(frame.columns)
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    lines.extend("| " + " | ".join(str(row[column]) for column in columns) + " |" for _, row in frame.iterrows())
    return lines


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", default="results/stage5c2g")
    args = parser.parse_args()
    root = ROOT / args.results
    decision = json.loads((root / "decision/stage5c2g_decision.json").read_text(encoding="utf-8"))
    fixed = pd.read_csv(root / "fixed_count_analysis/stage5c2g_fixed_count_summary.csv")[["hole_count", "mean_effect_db", "primary_bootstrap_se", "primary_ci_low", "primary_ci_high", "primary_negative", "estimator_conclusion_agreement"]]
    validity = json.loads((root / "validity_analysis/stage5c2g_validity_gate.json").read_text(encoding="utf-8"))
    lines = [
        "# Stage 5C.2G source-generated report", "",
        f"Fixed-count gate: **{'PASS' if decision['fixed_count_gate_passed'] else 'FAIL'}**", "",
        f"Small-system validity gate: **{'PASS' if decision['small_system_validity_gate_passed'] else 'FAIL'}**", "",
        f"Route: `{decision['route']}`", "",
        "Stage 5C3 production, Stage 5D, manuscript-result claims, and public release remain blocked.", "",
        "## Fixed-hole-count results", "", *markdown_table(fixed), "",
        "## Small-system validity gate", "", "```json", json.dumps(validity, indent=2), "```", "",
        "## Conservative interpretation", "",
        decision["interpretation"], "",
    ]
    (root / "STAGE5C2G_REPORT.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()

