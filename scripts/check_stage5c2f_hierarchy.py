#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from stage2_common import load_raw_config
from stage5c2f_common import planned_registry


def _single_mapping(df: pd.DataFrame, keys: list[str], value: str) -> bool:
    return bool(df.groupby(keys, dropna=False)[value].nunique(dropna=False).eq(1).all())


def audit_registry(registry: pd.DataFrame, raw: dict, confirmation: pd.DataFrame | None = None) -> tuple[pd.DataFrame, dict]:
    st = raw["stage5c2f"]
    design = st["design"]
    labels = list(st["labels"])
    required = {
        "label", "occupancy_idx", "path_idx", "phase_idx", "occupancy_seed",
        "hole_path_seed", "phase_batch_seed", "occupancy_realization_id",
        "path_realization_id", "phase_realization_id",
    }
    missing = sorted(required - set(registry.columns))
    checks: list[dict] = []

    def add(name: str, passed: bool, detail: str) -> None:
        checks.append({"check": name, "passed": bool(passed), "detail": detail})

    add("required_columns", not missing, "missing=" + ",".join(missing))
    if missing:
        return pd.DataFrame(checks), {"status": "FAIL", "failed_checks": ["required_columns"]}

    expected_rows = int(design["occupancies"]) * int(design["paths_per_occupancy"]) * int(design["phase_batches_per_path"]) * len(labels)
    add("exact_row_count", len(registry) == expected_rows, f"actual={len(registry)} expected={expected_rows}")
    cell_counts = registry.groupby(["occupancy_idx", "path_idx", "phase_idx", "label"]).size()
    add("complete_unique_grid", len(cell_counts) == expected_rows and cell_counts.eq(1).all(), f"unique_cells={len(cell_counts)}")
    add("one_occupancy_seed_per_level", _single_mapping(registry, ["occupancy_idx"], "occupancy_seed"), "nominal occupancy maps to one seed")
    add("one_occupancy_id_per_level", _single_mapping(registry, ["occupancy_idx"], "occupancy_realization_id"), "nominal occupancy maps to one immutable id")
    if "occupancy_hash" in registry.columns:
        add("one_occupancy_hash_per_level", _single_mapping(registry, ["occupancy_idx"], "occupancy_hash"), "nominal occupancy maps to one physical hash")
    add("one_path_seed_per_pair", _single_mapping(registry, ["occupancy_idx", "path_idx"], "hole_path_seed"), "path is nested within occupancy")
    add("one_path_id_per_pair", _single_mapping(registry, ["occupancy_idx", "path_idx"], "path_realization_id"), "path pair maps to one immutable id")
    add("one_phase_seed_per_cell", _single_mapping(registry, ["occupancy_idx", "path_idx", "phase_idx"], "phase_batch_seed"), "phase is nested within path")
    add("one_phase_id_per_cell", _single_mapping(registry, ["occupancy_idx", "path_idx", "phase_idx"], "phase_realization_id"), "phase cell maps to one immutable id")

    # Labels intentionally share a unit's seeds. Distinct physical units must not.
    unit_specs = [
        ("occupancy_seed", ["occupancy_idx"]),
        ("hole_path_seed", ["occupancy_idx", "path_idx"]),
        ("phase_batch_seed", ["occupancy_idx", "path_idx", "phase_idx"]),
    ]
    all_domain_seeds: dict[int, str] = {}
    collision_details = []
    for column, keys in unit_specs:
        units = registry[keys + [column]].drop_duplicates()
        add(f"unique_{column}_by_unit", units[column].nunique() == len(units), f"units={len(units)} unique={units[column].nunique()}")
        for value in units[column].astype(int):
            owner = all_domain_seeds.setdefault(value, column)
            if owner != column:
                collision_details.append(f"{value}:{owner}/{column}")
    add("cross_domain_seed_disjoint", not collision_details, ";".join(collision_details[:10]))

    if confirmation is not None:
        overlaps = []
        for column, _ in unit_specs:
            if column not in confirmation.columns:
                overlaps.append(f"missing:{column}")
                continue
            primary_values = set(registry[column].astype(int))
            confirmation_values = {int(v) for v in confirmation[column].dropna().astype(int) if int(v) != 0}
            common = sorted(primary_values & confirmation_values)
            if common:
                overlaps.append(f"{column}:{common[:5]}")
        add("primary_confirmation_seed_disjoint", not overlaps, ";".join(overlaps))

    failed = [row["check"] for row in checks if not row["passed"]]
    summary = {
        "stage": "stage5c2f_hierarchy_and_seed_namespace_gate",
        "design": st["preregistered_design"],
        "status": "PASS" if not failed else "FAIL",
        "failed_checks": failed,
    }
    return pd.DataFrame(checks), summary


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/stage5c2f/primary_lock.yaml")
    ap.add_argument("--registry")
    ap.add_argument("--locked-confirmation")
    ap.add_argument("--out", default="results/stage5c2f/preflight")
    ap.add_argument("--fail-on-collision", action="store_true")
    ap.add_argument("--fail-on-multiple-occupancy-hash", action="store_true")
    args = ap.parse_args()
    raw = load_raw_config(args.config)
    registry = pd.read_csv(ROOT / args.registry) if args.registry else planned_registry(raw)
    confirmation_path = args.locked_confirmation or raw["stage5c2f"]["locked_confirmation"]
    confirmation = pd.read_csv(ROOT / confirmation_path / "stage5c2d_seed_registry.csv")
    table, summary = audit_registry(registry, raw, confirmation)
    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    table.to_csv(out / "stage5c2f_hierarchy_invariants.csv", index=False)
    (out / "stage5c2f_hierarchy_gate.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    if summary["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
