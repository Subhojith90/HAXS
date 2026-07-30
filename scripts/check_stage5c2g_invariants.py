#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2g_common import domain_seed, load_yaml, planned_fixed_count_registry


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixed-config", default="configs/stage5c2g/fixed_count.yaml")
    parser.add_argument("--exact-config", default="configs/stage5c2g/exact_mobile_benchmark.yaml")
    parser.add_argument("--actual-results", default="results/stage5c2g/fixed_count")
    parser.add_argument("--require-actual", action="store_true")
    parser.add_argument("--out", default="results/stage5c2g/invariants")
    args = parser.parse_args()
    fixed_raw = load_yaml(args.fixed_config)
    fixed = fixed_raw["stage5c2g_fixed_count"]
    exact = load_yaml(args.exact_config)["stage5c2g_exact_benchmark"]
    checks = []

    def add(name: str, passed: bool, detail: str) -> None:
        checks.append({"check": name, "passed": bool(passed), "detail": detail})

    planned = pd.concat([planned_fixed_count_registry(fixed_raw, int(count)) for count in fixed["fixed_hole_counts"]], ignore_index=True)
    expected = len(fixed["fixed_hole_counts"]) * int(fixed["occupancies_per_count"]) * int(fixed["paths_per_occupancy"]) * int(fixed["phase_batches_per_path"]) * len(fixed["labels"])
    add("planned_fixed_count_row_count", len(planned) == expected, f"actual={len(planned)} expected={expected}")
    for value, keys in [
        ("occupancy_seed", ["hole_count", "occupancy_idx"]),
        ("hole_path_seed", ["hole_count", "occupancy_idx", "path_idx"]),
        ("phase_batch_seed", ["hole_count", "occupancy_idx", "path_idx", "phase_idx"]),
        ("occupancy_realization_id", ["hole_count", "occupancy_idx"]),
        ("path_realization_id", ["hole_count", "occupancy_idx", "path_idx"]),
        ("phase_realization_id", ["hole_count", "occupancy_idx", "path_idx", "phase_idx"]),
    ]:
        units = planned[[*keys, value]].drop_duplicates()
        add(f"unique_{value}_by_physical_unit", units[value].nunique() == len(units), f"units={len(units)} unique={units[value].nunique()}")
    domain_sets = {column: set(planned[column].astype(int)) for column in ["occupancy_seed", "hole_path_seed", "phase_batch_seed"]}
    add("fixed_count_cross_domain_seeds_disjoint", not ((domain_sets["occupancy_seed"] & domain_sets["hole_path_seed"]) | (domain_sets["occupancy_seed"] & domain_sets["phase_batch_seed"]) | (domain_sets["hole_path_seed"] & domain_sets["phase_batch_seed"])), "three fixed-count seed domains")
    prior = []
    for path in [ROOT / "results/stage5c2f/primary/stage5c2f_seed_registry.csv", ROOT / "results/stage5c2d_lite/confirmation/stage5c2d_seed_registry.csv"]:
        if path.is_file():
            prior.append(pd.read_csv(path))
    collisions = []
    for previous in prior:
        for column in domain_sets:
            old = {int(value) for value in previous[column].dropna().astype(int) if int(value) != 0}
            overlap = sorted(domain_sets[column] & old)
            if overlap:
                collisions.append(f"{column}:{overlap[:5]}")
    add("fixed_count_prior_blocks_seed_disjoint", not collisions, ";".join(collisions))
    exact_namespace = str(exact["namespace_uuid"])
    exact_seeds = set()
    for split in ["calibration", "validation"]:
        for case in exact[f"{split}_cases"]:
            exact_seeds.add(domain_seed(exact_namespace, split, "occupancy", case["id"]))
            for label in case.get("labels", exact["labels"]):
                for domain in ["path", "phase"]:
                    exact_seeds.add(domain_seed(exact_namespace, split, domain, case["id"], label))
    fixed_all = set().union(*domain_sets.values())
    prior_all = set()
    for previous in prior:
        for column in domain_sets:
            prior_all |= {int(value) for value in previous[column].dropna().astype(int) if int(value) != 0}
    add("exact_fixed_and_prior_seed_disjoint", not (exact_seeds & (fixed_all | prior_all)), f"exact_unique={len(exact_seeds)}")

    actual_root = ROOT / args.actual_results
    actual_paths = [actual_root / f"holes_{int(count):02d}/stage5c2g_fixed_count_seed_registry.csv" for count in fixed["fixed_hole_counts"]]
    if args.require_actual:
        add("actual_registries_present", all(path.is_file() for path in actual_paths), ";".join(str(path.relative_to(ROOT)) for path in actual_paths if not path.is_file()))
        if all(path.is_file() for path in actual_paths):
            actual = pd.concat([pd.read_csv(path) for path in actual_paths], ignore_index=True)
            mapping = actual.groupby(["hole_count", "occupancy_idx"]).occupancy_hash.nunique()
            add("one_actual_occupancy_hash_per_level", bool(mapping.eq(1).all()), f"max_hashes={int(mapping.max())}")
            path_mapping = actual.groupby(["hole_count", "occupancy_idx", "path_idx"]).path_realization_id.nunique()
            add("one_actual_path_id_per_pair", bool(path_mapping.eq(1).all()), f"max_ids={int(path_mapping.max())}")
    failed = [row["check"] for row in checks if not row["passed"]]
    summary = {"stage": "stage5c2g_invariant_gate", "status": "PASS" if not failed else "FAIL", "failed_checks": failed}
    output = ROOT / args.out
    output.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(checks).to_csv(output / "stage5c2g_invariants.csv", index=False)
    (output / "stage5c2g_invariant_gate.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
