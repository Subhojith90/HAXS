#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2g_common import assert_protocol_locked, load_yaml


def compare_curves(exact: pd.DataFrame, surrogate: pd.DataFrame) -> tuple[float, float]:
    merged = exact[["time", "xi2_db"]].merge(surrogate[["time", "xi2_db"]], on="time", suffixes=("_exact", "_surrogate"), validate="one_to_one")
    correlation = float(np.corrcoef(merged.xi2_db_exact, merged.xi2_db_surrogate)[0, 1])
    rmse = float(np.sqrt(np.mean((merged.xi2_db_exact - merged.xi2_db_surrogate) ** 2)))
    return correlation, rmse


def value_at(frame: pd.DataFrame, target: float) -> float:
    row = frame.iloc[int(np.argmin(np.abs(frame.time.to_numpy(float) - float(target))))]
    return float(row.xi2_db)


def main() -> None:
    raise SystemExit("REJECTED LEGACY ROUTE: Stage 5C.2G validity analysis is disabled")
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/stage5c2g/exact_mobile_benchmark.yaml")
    parser.add_argument("--protocol", default="configs/stage5c2g/protocol.yaml")
    parser.add_argument("--validation", default="results/stage5c2g/validation")
    parser.add_argument("--tolerances", default="results/stage5c2g/validity_tolerances/LOCKED.json")
    parser.add_argument("--out", default="results/stage5c2g/validity_analysis")
    args = parser.parse_args()
    protocol_lock = assert_protocol_locked()
    benchmark = load_yaml(args.config)["stage5c2g_exact_benchmark"]
    protocol = load_yaml(args.protocol)["stage5c2g_protocol"]
    tolerance = json.loads((ROOT / args.tolerances).read_text(encoding="utf-8"))
    if tolerance["protocol_candidate_sha256"] != protocol_lock["candidate_sha256"]:
        raise RuntimeError("validity tolerance lock belongs to a different protocol")
    root = ROOT / args.validation
    exact = pd.read_csv(root / "stage5c2g_exact_curves.csv")
    surrogate = pd.read_csv(root / "stage5c2g_surrogate_curves.csv")
    histories = pd.read_csv(root / "stage5c2g_exact_hole_configuration_history.csv")
    comparison_rows, contrast_rows, local_rows = [], [], []
    fixed_time = float(benchmark["fixed_time"])
    minimum_correlation = float(tolerance["minimum_time_profile_correlation"])
    maximum_rmse = float(tolerance["maximum_validation_rmse_db"])
    designated = {str(case["id"]): bool(case.get("designated_confirmatory", False)) for case in benchmark["validation_cases"]}

    for case_id, is_designated in designated.items():
        exact_case = exact[exact.case_id == case_id]
        surrogate_case = surrogate[surrogate.case_id == case_id]
        labels = sorted(set(exact_case.label) & set(surrogate_case.label))
        for label in labels:
            correlation, rmse = compare_curves(exact_case[exact_case.label == label], surrogate_case[surrogate_case.label == label])
            comparison_rows.append({"case_id": case_id, "label": label, "time_profile_correlation": correlation, "rmse_db": rmse, "correlation_pass": bool(np.isfinite(correlation) and correlation >= minimum_correlation), "rmse_pass": rmse <= maximum_rmse, "designated_confirmatory": is_designated})
        exact_static = value_at(exact_case[exact_case.label == "static_only"], fixed_time)
        surrogate_static = value_at(surrogate_case[surrogate_case.label == "static_only"], fixed_time)
        exact_effects, surrogate_effects = {}, {}
        for label in ["mobile_only", "spin_density_only", "combined"]:
            exact_effects[label] = exact_static - value_at(exact_case[exact_case.label == label], fixed_time)
            surrogate_effects[label] = surrogate_static - value_at(surrogate_case[surrogate_case.label == label], fixed_time)
            contrast_rows.append({"case_id": case_id, "label": label, "exact_effect_db": exact_effects[label], "surrogate_effect_db": surrogate_effects[label], "sign_agreement": bool(np.sign(exact_effects[label]) == np.sign(surrogate_effects[label])), "designated_confirmatory": is_designated})
        exact_order = sorted(exact_effects, key=exact_effects.get)
        surrogate_order = sorted(surrogate_effects, key=surrogate_effects.get)
        for row in contrast_rows:
            if row["case_id"] == case_id:
                row["component_ranking_agreement"] = exact_order == surrogate_order
                row["exact_ranking"] = ";".join(exact_order)
                row["surrogate_ranking"] = ";".join(surrogate_order)
        for offset in benchmark["local_window_offsets"]:
            target = fixed_time + float(offset)
            exact_effect = value_at(exact_case[exact_case.label == "static_only"], target) - value_at(exact_case[exact_case.label == "combined"], target)
            surrogate_effect = value_at(surrogate_case[surrogate_case.label == "static_only"], target) - value_at(surrogate_case[surrogate_case.label == "combined"], target)
            local_rows.append({"case_id": case_id, "offset": float(offset), "exact_effect_db": exact_effect, "surrogate_effect_db": surrogate_effect, "sign_agreement": bool(np.sign(exact_effect) == np.sign(surrogate_effect)), "designated_confirmatory": is_designated})

    comparisons = pd.DataFrame(comparison_rows)
    contrasts = pd.DataFrame(contrast_rows)
    local = pd.DataFrame(local_rows)
    expected_particles = exact["shape"].str.split("x").apply(lambda values: int(np.prod([int(value) for value in values]))) - exact.n_holes.astype(int)
    accounting = {
        "max_norm_error": float(exact.norm_error.max()),
        "max_particle_number_error": float(np.max(np.abs(exact.particle_number.to_numpy(float) - expected_particles.to_numpy(float)))),
        "max_hole_number_error": float(np.max(np.abs(exact.hole_number_expectation.to_numpy(float) - exact.n_holes.to_numpy(float)))),
        "max_hamiltonian_hermiticity_error": float(exact.hamiltonian_hermiticity_error.max()),
        "max_hole_configuration_probability_error": float(np.max(np.abs(histories.groupby(["case_id", "label", "time"]).probability.sum().to_numpy(float) - 1.0))),
    }
    accounting_pass = bool(all(value <= 1e-10 for value in accounting.values()))
    designated_comparisons = comparisons[comparisons.designated_confirmatory]
    designated_contrasts = contrasts[contrasts.designated_confirmatory]
    designated_local = local[local.designated_confirmatory]
    gate = {
        "stage": "stage5c2g_small_system_validity_gate",
        "time_profile_and_rmse_pass": bool(designated_comparisons.correlation_pass.all() and designated_comparisons.rmse_pass.all()),
        "sign_agreement_pass": bool(designated_contrasts.sign_agreement.all()),
        "component_ranking_agreement_pass": bool(designated_contrasts.component_ranking_agreement.all()),
        "local_window_sign_pass": bool(designated_local.sign_agreement.all()),
        "zero_coupling_limits_pass": bool(tolerance["zero_coupling_limits_pass"]),
        "exact_accounting_pass": accounting_pass,
        "accounting": accounting,
        "minimum_time_profile_correlation": minimum_correlation,
        "maximum_validation_rmse_db": maximum_rmse,
    }
    gate["passed"] = bool(gate["time_profile_and_rmse_pass"] and gate["sign_agreement_pass"] and gate["component_ranking_agreement_pass"] and gate["local_window_sign_pass"] and gate["zero_coupling_limits_pass"] and gate["exact_accounting_pass"])
    output = ROOT / args.out
    output.mkdir(parents=True, exist_ok=True)
    comparisons.to_csv(output / "stage5c2g_time_profile_comparison.csv", index=False)
    contrasts.to_csv(output / "stage5c2g_component_contrasts.csv", index=False)
    local.to_csv(output / "stage5c2g_local_window_validity.csv", index=False)
    (output / "stage5c2g_validity_gate.json").write_text(json.dumps(gate, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(gate, indent=2))


if __name__ == "__main__":
    main()
