#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from haxs.lattice.graphs import hypercubic_lattice
from haxs.methods.dtwa import run_dtwa
from stage5c2gR32_common import (
    atomic_write_json,
    file_manifest,
    require_new_output,
    sha256_payload,
)


def _wilson(successes: int, trials: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if trials <= 0:
        raise ValueError("Wilson interval requires at least one trial")
    p = successes / trials
    denominator = 1.0 + z * z / trials
    centre = (p + z * z / (2.0 * trials)) / denominator
    radius = (
        z
        * math.sqrt(p * (1.0 - p) / trials + z * z / (4.0 * trials * trials))
        / denominator
    )
    return max(0.0, centre - radius), min(1.0, centre + radius)


def _critical_value(rule: str, alpha: float, family_size: int) -> float:
    normal = statistics.NormalDist()
    if rule == "bonferroni_one_sided_normal_envelope":
        tail = alpha / (2.0 * family_size)
    elif rule == "sidak_one_sided_normal_envelope":
        tail = (1.0 - (1.0 - alpha) ** (1.0 / (2.0 * family_size)))
    else:
        raise ValueError(f"unsupported analytic rule: {rule}")
    return normal.inv_cdf(1.0 - tail)


def _seed(namespace: str, case_id: str, index: int) -> int:
    import hashlib

    digest = hashlib.sha256(f"{namespace}|{case_id}|{index}".encode()).digest()
    return int.from_bytes(digest[:8], "big") % (2**32 - 1)


def _case_map(quadrature_config: dict) -> dict[str, dict]:
    stage = quadrature_config["stage5c2gR32_G1"]
    return {str(case["id"]): case for case in stage["cases"]}


def _evaluate_seed(
    case: dict,
    seed_index: int,
    phase_seed: int,
    trajectories: int,
    family_alpha: float,
    primary_rule: str,
    offsets: list[float],
    namespace: str,
    model: dict,
    times: np.ndarray,
) -> tuple[list[dict], dict]:
    graph = hypercubic_lattice(tuple(case["shape"]), False)
    occupancy_spec = case["occupancies"][0]
    holes = list(map(int, occupancy_spec["holes"]))
    occupancy = np.ones(graph.n_sites, dtype=bool)
    occupancy[holes] = False
    particles = int(occupancy.sum())
    result = run_dtwa(
        graph,
        times,
        j_perp=float(model["j_perp"]),
        jz=float(model["jz"]),
        mobile_eta=0.0,
        lambda_sd=0.0,
        n_traj=trajectories,
        initial_occupancy=occupancy,
        fixed_hole_count=len(holes),
        phase_batch_seed=phase_seed,
        integration_substeps=4,
        return_component_statistics=True,
    )
    stats = result["component_statistics"]
    family_size = len(stats) * 3
    critical = _critical_value(primary_rule, family_alpha, family_size)
    sidak_critical = _critical_value(
        "sidak_one_sided_normal_envelope", family_alpha, family_size
    )
    bound = particles / 2.0
    raw_rows = []
    rejected = False
    sidak_rejected = False
    maximum_standardized_excess = -float("inf")
    for item in stats:
        for component in ["Sx", "Sy", "Sz"]:
            mean = float(item[f"{component}_mean"])
            se = float(item[f"{component}_se"])
            lower = mean - critical * se
            upper = mean + critical * se
            cell_reject = lower > bound or upper < -bound
            rejected = rejected or cell_reject
            sidak_rejected = sidak_rejected or (
                mean - sidak_critical * se > bound
                or mean + sidak_critical * se < -bound
            )
            standardized = (
                (abs(mean) - bound) / se
                if se > 0.0
                else (float("inf") if abs(mean) > bound else -float("inf"))
            )
            maximum_standardized_excess = max(maximum_standardized_excess, standardized)
            raw_rows.append(
                {
                    "schema_version": "haxs.stage5c2gR32.batch-statistics.v1",
                    "case_id": case["id"],
                    "occupancy_id": occupancy_spec["occupancy_id"],
                    "seed_index": seed_index,
                    "phase_batch_seed": phase_seed,
                    "time": item["time"],
                    "component": component,
                    "mean": mean,
                    "standard_error": se,
                    "particle_half_bound": bound,
                    "critical_value": critical,
                    "simultaneous_lower": lower,
                    "simultaneous_upper": upper,
                    "cell_reject": cell_reject,
                }
            )
    detection = {}
    # A controlled injected fixture is defined at the physical boundary, with
    # the observed finite-batch standard errors retained. This tests whether
    # the rule detects a declared excess rather than merely an arbitrary value.
    positive_standard_errors = [
        float(row["standard_error"])
        for row in raw_rows
        if row["component"] == "Sx"
        and abs(float(row["mean"])) >= 0.99 * bound
        and float(row["standard_error"]) > 0
    ]
    if not positive_standard_errors:
        raise RuntimeError("calibration fixture has no near-boundary Sx standard error")
    fixture_se = float(np.median(positive_standard_errors))
    for offset in offsets:
        injected_mean = bound * (1.0 + float(offset))
        detection[str(offset)] = bool(injected_mean - critical * fixture_se > bound)
    summary = {
        "case_id": case["id"],
        "seed_index": seed_index,
        "phase_batch_seed": phase_seed,
        "family_size": family_size,
        "critical_value": critical,
        "benign_rejected": rejected,
        "sidak_benign_rejected": sidak_rejected,
        "maximum_standardized_excess": maximum_standardized_excess,
        "fixture_standard_error": fixture_se,
        "injected_detection": detection,
    }
    return raw_rows, summary


def calibrate(config_path: Path, out: Path) -> dict:
    s02_path = ROOT / "output/stage5c2gR32/g1_preflight/verification.json"
    if not s02_path.is_file() or json.loads(s02_path.read_text(encoding="utf-8")).get(
        "status"
    ) != "PASS":
        raise RuntimeError("S03 is blocked until deterministic S02 passes")
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    stage = config["stage5c2gR32_sanity_calibration"]
    quadrature_config = yaml.safe_load(
        (ROOT / "configs/stage5c2gR32/g1_phase_quadrature.yaml").read_text(
            encoding="utf-8"
        )
    )
    qstage = quadrature_config["stage5c2gR32_G1"]
    cases = _case_map(quadrature_config)
    output = require_new_output(out)
    atomic_write_json(
        output / "FROZEN_CALIBRATION_POLICY.json",
        {
            "schema_version": stage["schema_version"],
            "config_sha256": __import__("hashlib").sha256(
                config_path.read_bytes()
            ).hexdigest(),
            "immutable_fields": {
                name: stage[name] if name in stage else stage["pass_criteria"][name]
                for name in stage["immutable_after_first_output"]
            },
            "binding_sesoi": stage[
                "binding_sesoi_fraction_of_half_particle_count"
            ],
        },
    )
    times = np.linspace(
        float(qstage["times"]["start"]),
        float(qstage["times"]["stop"]),
        int(qstage["times"]["points"]),
    )
    seeds_per_case = int(stage["benign_seeds_per_case"])
    if seeds_per_case * len(stage["cases"]) < int(stage["minimum_total_benign_seeds"]):
        raise RuntimeError("calibration configuration has fewer than 1000 benign seeds")
    chunk_size = int(stage["chunk_size"])
    summaries: list[dict] = []
    chunk_index = 0
    for case_id in stage["cases"]:
        case = cases[str(case_id)]
        for start in range(0, seeds_per_case, chunk_size):
            chunk_rows: list[dict] = []
            chunk_summaries: list[dict] = []
            for seed_index in range(start, min(start + chunk_size, seeds_per_case)):
                phase_seed = _seed(stage["namespace_uuid"], str(case_id), seed_index)
                raw, summary = _evaluate_seed(
                    case,
                    seed_index,
                    phase_seed,
                    int(stage["trajectories_per_seed"]),
                    float(stage["familywise_alpha"]),
                    str(stage["primary_rule"]),
                    list(
                        map(
                            float,
                            stage[
                                "injected_offsets_fraction_of_half_particle_count"
                            ],
                        )
                    ),
                    stage["namespace_uuid"],
                    qstage["model"],
                    times,
                )
                chunk_rows.extend(raw)
                chunk_summaries.append(summary)
                summaries.append(summary)
            temporary = output / f".chunk_{chunk_index:04d}.partial.csv"
            final = output / f"batch_statistics_chunk_{chunk_index:04d}.csv"
            pd.DataFrame(chunk_rows).to_csv(temporary, index=False)
            os.replace(temporary, final)
            atomic_write_json(
                output / f"seed_summary_chunk_{chunk_index:04d}.json",
                {"rows": chunk_summaries},
            )
            chunk_index += 1

    summary_frame = pd.DataFrame(
        [
            {
                **{key: row[key] for key in ["case_id", "seed_index", "phase_batch_seed", "family_size", "critical_value", "benign_rejected", "maximum_standardized_excess", "fixture_standard_error"]},
                "sidak_benign_rejected": row["sidak_benign_rejected"],
                **{
                    f"detected_offset_{offset}": detected
                    for offset, detected in row["injected_detection"].items()
                },
            }
            for row in summaries
        ]
    )
    summary_frame.to_csv(output / "calibration_grid.csv", index=False)
    trials = len(summary_frame)
    false_rejections = int(summary_frame["benign_rejected"].sum())
    false_rate = false_rejections / trials
    false_interval = _wilson(false_rejections, trials)
    power_rows = []
    for offset in stage["injected_offsets_fraction_of_half_particle_count"]:
        column = f"detected_offset_{float(offset)}"
        detections = int(summary_frame[column].sum())
        interval = _wilson(detections, trials)
        power_rows.append(
            {
                "offset_fraction_of_half_particle_count": float(offset),
                "detections": detections,
                "trials": trials,
                "detection_rate": detections / trials,
                "lower_95": interval[0],
                "upper_95": interval[1],
            }
        )
    pd.DataFrame(power_rows).to_csv(output / "power_by_violation_size.csv", index=False)
    empirical_threshold = float(
        np.quantile(
            summary_frame["maximum_standardized_excess"].replace(
                [np.inf, -np.inf], np.nan
            ).dropna(),
            1.0 - float(stage["familywise_alpha"]),
            method="higher",
        )
    )
    comparison_rows = [
        {
            "rule": stage["primary_rule"],
            "benign_false_rejections": false_rejections,
            "benign_trials": trials,
            "benign_false_rejection_rate": false_rate,
            "calibration_role": "PRIMARY_PREREGISTERED",
        },
        {
            "rule": "sidak_one_sided_normal_envelope",
            "benign_false_rejections": int(
                summary_frame["sidak_benign_rejected"].sum()
            ),
            "benign_trials": trials,
            "benign_false_rejection_rate": float(
                summary_frame["sidak_benign_rejected"].mean()
            ),
            "calibration_role": "COMPARATOR_ONLY",
        },
        {
            "rule": "empirical_max_t",
            "benign_false_rejections": int(
                (
                    summary_frame["maximum_standardized_excess"]
                    > empirical_threshold
                ).sum()
            ),
            "benign_trials": trials,
            "benign_false_rejection_rate": float(
                (
                    summary_frame["maximum_standardized_excess"]
                    > empirical_threshold
                ).mean()
            ),
            "calibration_role": "COMPARATOR_ONLY",
            "empirical_threshold": empirical_threshold,
        },
    ]
    pd.DataFrame(comparison_rows).to_csv(output / "rule_comparison.csv", index=False)
    binding = float(stage["binding_sesoi_fraction_of_half_particle_count"])
    binding_row = next(
        row
        for row in power_rows
        if row["offset_fraction_of_half_particle_count"] == binding
    )
    criteria = stage["pass_criteria"]
    half_width = (false_interval[1] - false_interval[0]) / 2.0
    passed = (
        false_rate <= float(criteria["maximum_benign_familywise_false_rejection"])
        and false_interval[1] <= float(criteria["maximum_upper_95_interval"])
        and binding_row["detection_rate"]
        >= float(criteria["minimum_binding_sesoi_detection"])
        and half_width <= float(criteria["maximum_monte_carlo_half_width"])
    )
    decision = {
        "schema_version": stage["schema_version"],
        "stage": "S03",
        "status": "PASS" if passed else "FAIL",
        "primary_rule": stage["primary_rule"],
        "familywise_alpha": stage["familywise_alpha"],
        "benign_trials": trials,
        "benign_false_rejections": false_rejections,
        "benign_false_rejection_rate": false_rate,
        "benign_false_rejection_interval_95": list(false_interval),
        "benign_interval_half_width": half_width,
        "binding_sesoi": binding,
        "binding_sesoi_detection_rate": binding_row["detection_rate"],
        "power": power_rows,
        "extension_permitted": bool(
            not passed
            and half_width
            > float(
                stage["seed_extension"][
                    "permitted_only_if_interval_half_width_exceeds"
                ]
            )
        ),
        "next": "BUILD_R32_CANDIDATE" if passed else "STOP_OR_PREDECLARED_EXTENSION_ONLY",
    }
    decision["decision_sha256"] = sha256_payload(decision)
    atomic_write_json(output / "calibration_decision.json", decision)
    manifest = {
        "schema_version": "haxs.stage5c2gR32.S03-manifest.v1",
        "files": file_manifest(output),
    }
    manifest["manifest_sha256"] = sha256_payload(manifest)
    atomic_write_json(output / "MANIFEST.json", manifest)
    return decision


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "configs/stage5c2gR32/sanity_calibration.yaml",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "output/stage5c2gR32/sanity_calibration",
    )
    args = parser.parse_args()
    result = calibrate(args.config, args.out)
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
