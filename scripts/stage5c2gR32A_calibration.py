from __future__ import annotations

import json
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from stage5c2gR32_common import atomic_write_json, require_new_output, sha256_file, sha256_payload
from stage5c2gR32A_common import (
    COMPONENTS,
    ROOT,
    analytic_normal_power,
    critical_value,
    sample_counts,
    sampled_statistics,
    seed,
    verify_population,
    verify_unit_registry,
    wilson,
    write_manifest,
)


def _load_inputs(stage: dict) -> tuple[list[dict], dict[str, dict]]:
    registry_path = ROOT / stage["canonical_unit_registry"]
    population_path = ROOT / stage["deterministic_truth"]
    units = verify_unit_registry(pd.read_csv(registry_path))
    population = pd.read_csv(population_path)
    verify_population(population, units)
    arrays: dict[str, dict] = {}
    for unit in units:
        unit_id = str(unit["unit_id"])
        subset = population[population["unit_id"].astype(str) == unit_id].sort_values(
            ["node_index", "time_index"]
        )
        values = subset[list(COMPONENTS)].to_numpy(float).reshape(1024, 45, 3)
        arrays[unit_id] = {
            "values": values.reshape(1024, 135),
            "truth": values.mean(axis=0).reshape(135),
            "case_id": str(unit["case_id"]),
            "occupancy_id": str(unit["occupancy_id"]),
            "bound": float(unit["particle_count"]) / 2.0,
        }
    return units, arrays


def _evaluate(
    stage: dict,
    units: list[dict],
    arrays: dict[str, dict],
    method: str,
    trajectories: int,
    families: int,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    alpha = float(stage["familywise_alpha"])
    offset = float(stage["binding_sesoi_fraction_of_half_particle_count"])
    challenge_component = COMPONENTS.index(str(stage["challenge_component"]))
    challenge_time_index = int(stage["challenge_time_index"])
    challenge_cell = challenge_time_index * len(COMPONENTS) + challenge_component
    global_critical = critical_value(alpha, len(units) * 45 * len(COMPONENTS))
    case_unit_counts = pd.Series([str(unit["case_id"]) for unit in units]).value_counts().to_dict()
    case_critical = {
        case_id: critical_value(alpha, int(count) * 45 * len(COMPONENTS))
        for case_id, count in case_unit_counts.items()
    }
    unit_critical = critical_value(alpha, 45 * len(COMPONENTS))
    family_rows: list[dict] = []
    seed_rows: list[dict] = []
    aggregate_errors: dict[str, list[np.ndarray]] = defaultdict(list)
    aggregate_ses: dict[str, list[np.ndarray]] = defaultdict(list)

    for family_index in range(families):
        global_reject = False
        global_covered = True
        global_detect = False
        case_reject = defaultdict(bool)
        case_covered = defaultdict(lambda: True)
        case_detect = defaultdict(bool)
        unit_detect: dict[str, bool] = {}
        global_max = -np.inf
        for unit in units:
            unit_id = str(unit["unit_id"])
            info = arrays[unit_id]
            phase_seed = seed(stage["namespace_uuid"], stage["block"], family_index, unit_id, method)
            generator = np.random.default_rng(phase_seed)
            counts = sample_counts(method, trajectories, 1024, generator)
            means, ses = sampled_statistics(info["values"], counts)
            truth = info["truth"]
            errors = means - truth
            aggregate_errors[unit_id].append(errors)
            aggregate_ses[unit_id].append(ses)
            bound = float(info["bound"])
            standardized_excess = np.full_like(means, -np.inf)
            positive = ses > 0.0
            standardized_excess[positive] = (np.abs(means[positive]) - bound) / ses[positive]
            standardized_excess[~positive & (np.abs(means) > bound)] = np.inf
            unit_global_reject = bool(np.any(standardized_excess > global_critical))
            unit_case_reject = bool(np.any(standardized_excess > case_critical[info["case_id"]]))
            covered_global = bool(
                np.all(np.abs(errors[positive]) <= global_critical * ses[positive])
                and np.all(np.abs(errors[~positive]) <= 1.0e-14)
            )
            covered_case = bool(
                np.all(np.abs(errors[positive]) <= case_critical[info["case_id"]] * ses[positive])
                and np.all(np.abs(errors[~positive]) <= 1.0e-14)
            )
            alternative_mean = (
                means[challenge_cell]
                - truth[challenge_cell]
                + bound * (1.0 + offset)
            )
            alternative_detect = bool(
                alternative_mean - unit_critical * ses[challenge_cell] > bound
            )
            global_reject = global_reject or unit_global_reject
            global_covered = global_covered and covered_global
            global_detect = global_detect or alternative_detect
            case_reject[info["case_id"]] = case_reject[info["case_id"]] or unit_case_reject
            case_covered[info["case_id"]] = case_covered[info["case_id"]] and covered_case
            case_detect[info["case_id"]] = case_detect[info["case_id"]] or alternative_detect
            unit_detect[unit_id] = alternative_detect
            global_max = max(global_max, float(np.max(standardized_excess)))
            seed_rows.append(
                {
                    "block": stage["block"],
                    "family_index": family_index,
                    "unit_id": unit_id,
                    "case_id": info["case_id"],
                    "occupancy_id": info["occupancy_id"],
                    "sampling": method,
                    "trajectories": trajectories,
                    "phase_seed": phase_seed,
                }
            )
        row = {
            "block": stage["block"],
            "sampling": method,
            "trajectories": trajectories,
            "family_index": family_index,
            "global_false_reject": global_reject,
            "global_simultaneous_coverage": global_covered,
            "global_binding_sesoi_detect": global_detect,
            "global_max_standardized_excess": global_max,
        }
        for case_id in sorted(case_unit_counts):
            row[f"case_false_reject::{case_id}"] = case_reject[case_id]
            row[f"case_simultaneous_coverage::{case_id}"] = case_covered[case_id]
            row[f"case_binding_sesoi_detect::{case_id}"] = case_detect[case_id]
        for unit in units:
            row[f"unit_binding_sesoi_detect::{unit['unit_id']}"] = unit_detect[str(unit["unit_id"])]
        family_rows.append(row)

    bias_rows = []
    for unit in units:
        unit_id = str(unit["unit_id"])
        errors = np.vstack(aggregate_errors[unit_id])
        ses = np.vstack(aggregate_ses[unit_id])
        mean_error = errors.mean(axis=0)
        empirical_rmse = float(np.sqrt(np.mean(errors * errors)))
        mean_reported_se = float(np.mean(ses))
        standard_error_of_bias = np.maximum(
            errors.std(axis=0, ddof=1) / np.sqrt(float(families)), 1.0e-15
        )
        bias_rows.append(
            {
                "unit_id": unit_id,
                "case_id": unit["case_id"],
                "occupancy_id": unit["occupancy_id"],
                "maximum_absolute_standardized_aggregate_bias": float(
                    np.max(np.abs(mean_error) / standard_error_of_bias)
                ),
                "rmse": empirical_rmse,
                "mean_reported_standard_error": mean_reported_se,
                "rmse_to_mean_se_ratio": empirical_rmse / mean_reported_se,
            }
        )
    meta = {
        "global_critical_value": global_critical,
        "case_critical_values": case_critical,
        "unit_critical_value": unit_critical,
        "family_size": len(units) * 45 * len(COMPONENTS),
        "alternative_definition": (
            "independent family resample error shifted to a population with "
            "mean B*(1+SESOI) at the frozen challenge cell"
        ),
        "challenge_cell": {
            "time_index": challenge_time_index,
            "component": stage["challenge_component"],
        },
    }
    return pd.DataFrame(family_rows), pd.DataFrame(seed_rows), {
        "bias_rows": bias_rows,
        **meta,
    }


def _operating_rows(families: pd.DataFrame, units: list[dict]) -> list[dict]:
    scopes = [
        ("GLOBAL", "global_false_reject", "global_binding_sesoi_detect", "global_simultaneous_coverage")
    ]
    for case_id in sorted({str(unit["case_id"]) for unit in units}):
        scopes.append(
            (
                f"CASE::{case_id}",
                f"case_false_reject::{case_id}",
                f"case_binding_sesoi_detect::{case_id}",
                f"case_simultaneous_coverage::{case_id}",
            )
        )
    for unit in units:
        scopes.append(
            (
                f"UNIT::{unit['occupancy_id']}",
                None,
                f"unit_binding_sesoi_detect::{unit['unit_id']}",
                None,
            )
        )
    rows = []
    for scope, false_column, power_column, coverage_column in scopes:
        trials = len(families)
        detections = int(families[power_column].sum())
        power_interval = wilson(detections, trials)
        row = {
            "scope": scope,
            "trials": trials,
            "binding_sesoi_detections": detections,
            "binding_sesoi_power": detections / trials,
            "binding_sesoi_power_lower_95": power_interval[0],
            "binding_sesoi_power_upper_95": power_interval[1],
        }
        if false_column:
            false_rejections = int(families[false_column].sum())
            false_interval = wilson(false_rejections, trials)
            coverages = int(families[coverage_column].sum())
            coverage_interval = wilson(coverages, trials)
            row.update(
                {
                    "false_rejections": false_rejections,
                    "false_rejection_rate": false_rejections / trials,
                    "false_rejection_lower_95": false_interval[0],
                    "false_rejection_upper_95": false_interval[1],
                    "simultaneous_coverages": coverages,
                    "simultaneous_coverage_rate": coverages / trials,
                    "simultaneous_coverage_lower_95": coverage_interval[0],
                    "simultaneous_coverage_upper_95": coverage_interval[1],
                }
            )
        rows.append(row)
    return rows


def run_development(config_path: Path, out: Path) -> dict:
    stage = yaml.safe_load(config_path.read_text(encoding="utf-8"))["stage5c2gR32A_stochastic"]
    if stage["block"] != "DEVELOPMENT":
        raise RuntimeError("development runner received a non-development config")
    deterministic = ROOT / "output/stage5c2gR32A/g1_preflight/verification.json"
    if not deterministic.is_file() or json.loads(deterministic.read_text()).get("status") != "PASS":
        raise RuntimeError("stochastic development is blocked until deterministic preflight passes")
    output = require_new_output(out)
    units, arrays = _load_inputs(stage)
    all_families, all_seeds, comparisons = [], [], []
    started = time.monotonic()
    for method in stage["candidate_sampling_rules"]:
        for trajectories in stage["candidate_trajectory_budgets"]:
            families, seeds, meta = _evaluate(
                stage, units, arrays, str(method), int(trajectories), int(stage["development_families"])
            )
            all_families.append(families)
            all_seeds.append(seeds)
            operating = _operating_rows(families, units)
            global_row = next(row for row in operating if row["scope"] == "GLOBAL")
            comparisons.append(
                {
                    "sampling": method,
                    "trajectories": int(trajectories),
                    "global_false_rejection_upper_95": global_row["false_rejection_upper_95"],
                    "global_binding_power_lower_95": global_row["binding_sesoi_power_lower_95"],
                    "global_simultaneous_coverage_lower_95": global_row["simultaneous_coverage_lower_95"],
                    "analytic_binding_power_by_unit": json.dumps(
                        {
                            unit["occupancy_id"]: analytic_normal_power(
                                arrays[str(unit["unit_id"])]["bound"]
                                * float(stage["binding_sesoi_fraction_of_half_particle_count"]),
                                float(
                                    np.std(
                                        arrays[str(unit["unit_id"])]["values"][
                                            :, int(stage["challenge_time_index"]) * 3
                                        ],
                                        ddof=1,
                                    )
                                    / np.sqrt(float(trajectories))
                                ),
                                meta["unit_critical_value"],
                            )
                            for unit in units
                        },
                        sort_keys=True,
                    ),
                }
            )
    pd.concat(all_families, ignore_index=True).to_csv(output / "development_family_statistics.csv", index=False)
    pd.concat(all_seeds, ignore_index=True).to_csv(output / "development_seed_registry.csv", index=False)
    pd.DataFrame(comparisons).to_csv(output / "development_rule_comparison.csv", index=False)
    frozen_rule = stage["primary_rule_frozen_for_validation"]
    frozen = {
        "schema_version": "haxs.stage5c2gR32A.frozen-rule.v1",
        "rule": frozen_rule,
        "development_config_sha256": sha256_file(config_path),
        "selection_timing": "FROZEN_BEFORE_VALIDATION_OPENING",
        "selection_basis": "supervisor-prespecified IID 4096 budget; development comparators are non-binding",
    }
    frozen["rule_sha256"] = sha256_payload(frozen)
    atomic_write_json(output / "FROZEN_RULE.json", frozen)
    decision = {
        "schema_version": stage["schema_version"],
        "stage": "R3.2A-S03-DEVELOPMENT",
        "status": "PASS",
        "role": "NON_AUTHORISING_RULE_COMPARISON",
        "canonical_units": len(units),
        "candidate_methods": stage["candidate_sampling_rules"],
        "candidate_trajectory_budgets": stage["candidate_trajectory_budgets"],
        "families_per_design": stage["development_families"],
        "frozen_rule": frozen_rule,
        "frozen_rule_sha256": frozen["rule_sha256"],
        "elapsed_seconds": time.monotonic() - started,
        "validation_opened": False,
        "candidate_created": False,
        "next": "UNTOUCHED_VALIDATION",
    }
    decision["decision_sha256"] = sha256_payload(decision)
    atomic_write_json(output / "decision.json", decision)
    manifest = write_manifest(output, "haxs.stage5c2gR32A.development-manifest.v1")
    decision["manifest_sha256"] = manifest["manifest_sha256"]
    return decision


def run_validation(config_path: Path, out: Path) -> dict:
    stage = yaml.safe_load(config_path.read_text(encoding="utf-8"))["stage5c2gR32A_stochastic"]
    if stage["block"] != "VALIDATION":
        raise RuntimeError("validation runner received a non-validation config")
    development_path = ROOT / stage["development_result"]
    development = json.loads(development_path.read_text(encoding="utf-8"))
    if development.get("status") != "PASS" or development.get("validation_opened") is not False:
        raise RuntimeError("validation is blocked by development state")
    frozen_path = development_path.parent / "FROZEN_RULE.json"
    frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
    if frozen["rule"] != stage["frozen_rule"] or frozen["rule_sha256"] != development["frozen_rule_sha256"]:
        raise RuntimeError("validation rule differs from the pre-open frozen rule")
    output = require_new_output(out)
    atomic_write_json(
        output / "VALIDATION_OPENED.json",
        {
            "schema_version": "haxs.stage5c2gR32A.validation-open.v1",
            "validation_config_sha256": sha256_file(config_path),
            "development_decision_sha256": sha256_file(development_path),
            "frozen_rule_sha256": frozen["rule_sha256"],
            "extension_permitted": bool(stage["extension"]["permitted"]),
        },
    )
    units, arrays = _load_inputs(stage)
    started = time.monotonic()
    rule = stage["frozen_rule"]
    families, seeds, meta = _evaluate(
        stage,
        units,
        arrays,
        str(rule["sampling"]),
        int(rule["trajectories"]),
        int(stage["validation_families"]),
    )
    development_seeds = pd.read_csv(development_path.parent / "development_seed_registry.csv")
    collision = sorted(set(development_seeds["phase_seed"].astype(int)) & set(seeds["phase_seed"].astype(int)))
    if collision:
        raise RuntimeError("development/validation seed collision")
    families.to_csv(output / "validation_family_statistics.csv", index=False)
    seeds.to_csv(output / "validation_seed_registry.csv", index=False)
    pd.DataFrame(meta["bias_rows"]).to_csv(output / "truth_error_metrics.csv", index=False)
    operating = _operating_rows(families, units)
    pd.DataFrame(operating).to_csv(output / "operating_characteristics.csv", index=False)
    atomic_write_json(
        output / "seed_collision_report.json",
        {
            "development_namespace": yaml.safe_load(
                (ROOT / stage["development_config"]).read_text(encoding="utf-8")
            )["stage5c2gR32A_stochastic"]["namespace_uuid"],
            "validation_namespace": stage["namespace_uuid"],
            "development_seed_count": int(len(development_seeds)),
            "validation_seed_count": int(len(seeds)),
            "collisions": collision,
            "passed": not collision,
        },
    )
    criteria = stage["pass_criteria"]
    required_scopes = [row for row in operating if row["scope"] == "GLOBAL" or row["scope"].startswith("CASE::")]
    all_power_scopes = operating
    bias = meta["bias_rows"]
    bias_limit = float(stage["truth_metrics"]["maximum_absolute_standardized_aggregate_bias"])
    ratio_low, ratio_high = map(float, stage["truth_metrics"]["rmse_to_mean_se_ratio"])
    passed = bool(
        all(row["false_rejection_upper_95"] <= float(criteria["maximum_false_rejection_upper_95"]) for row in required_scopes)
        and all(row["binding_sesoi_power_lower_95"] >= float(criteria["minimum_binding_power_lower_95"]) for row in all_power_scopes)
        and all(row["simultaneous_coverage_lower_95"] >= float(criteria["minimum_simultaneous_coverage_lower_95"]) for row in required_scopes)
        and all(row["maximum_absolute_standardized_aggregate_bias"] <= bias_limit for row in bias)
        and all(ratio_low <= row["rmse_to_mean_se_ratio"] <= ratio_high for row in bias)
    )
    decision = {
        "schema_version": stage["schema_version"],
        "stage": "R3.2A-S03-VALIDATION",
        "status": "PASS" if passed else "FAIL",
        "role": "NON_AUTHORISING_SCALE_EXTENSION_CALIBRATION",
        "untouched_validation": True,
        "canonical_units": len(units),
        "global_family_size": meta["family_size"],
        "validation_families": stage["validation_families"],
        "frozen_rule": rule,
        "frozen_rule_sha256": frozen["rule_sha256"],
        "alternative_definition": meta["alternative_definition"],
        "operating_characteristics": operating,
        "truth_error_metrics": bias,
        "seed_collision_count": 0,
        "extension_permitted": False,
        "elapsed_seconds": time.monotonic() - started,
        "candidate_created": False,
        "next": "SUPERVISORY_PRE_CANDIDATE_REVIEW",
    }
    decision["decision_sha256"] = sha256_payload(decision)
    atomic_write_json(output / "decision.json", decision)
    manifest = write_manifest(output, "haxs.stage5c2gR32A.validation-manifest.v1")
    decision["manifest_sha256"] = manifest["manifest_sha256"]
    return decision
