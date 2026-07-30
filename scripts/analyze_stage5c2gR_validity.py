#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from haxs.lattice.graphs import hypercubic_lattice
from haxs.validation.transport import transport_discrepancy
from stage5c2gR_common import assert_protocol_locked, checked_lock, load_yaml, sha256_payload

UNIT = ["case_id", "occupancy_idx", "path_idx", "phase_idx", "label"]


def curve_metrics(exact: pd.DataFrame, surrogate: pd.DataFrame) -> tuple[float, float]:
    merged = exact[["time", "xi2_db"]].merge(surrogate[["time", "xi2_db"]], on="time", suffixes=("_exact", "_surrogate"), validate="one_to_one")
    return float(np.corrcoef(merged.xi2_db_exact, merged.xi2_db_surrogate)[0, 1]), float(np.sqrt(np.mean((merged.xi2_db_exact - merged.xi2_db_surrogate) ** 2)))


def value_at(frame: pd.DataFrame, target: float) -> float:
    row = frame.iloc[int(np.argmin(np.abs(frame.time.to_numpy(float) - target)))]
    return float(row.xi2_db)


def ranking_agrees(exact: dict[str, float], surrogate: dict[str, float], tolerance: float) -> bool:
    for left, right in combinations(sorted(exact), 2):
        exact_difference = exact[left] - exact[right]
        surrogate_difference = surrogate[left] - surrogate[right]
        exact_tie = abs(exact_difference) <= tolerance
        surrogate_tie = abs(surrogate_difference) <= tolerance
        if exact_tie != surrogate_tie:
            return False
        if not exact_tie and np.sign(exact_difference) != np.sign(surrogate_difference):
            return False
    return True


def configuration_distribution(frame: pd.DataFrame, case_id: str, occupancy_idx: int, label: str, method: str) -> list[dict[tuple[int, ...], float]]:
    subset = frame[(frame.case_id == case_id) & (frame.occupancy_idx == occupancy_idx) & (frame.label == label) & (frame.method == method)]
    output = []
    for _, at_time in subset.groupby("time", sort=True):
        units = at_time[["path_idx", "phase_idx"]].drop_duplicates().shape[0]
        probabilities = at_time.groupby("hole_configuration").probability.sum() / max(1, units)
        output.append({tuple(int(v) for v in str(key).split(";") if str(v) != ""): float(value) for key, value in probabilities.items()})
    return output


def main() -> None:
    raise SystemExit("BLOCKED LEGACY ROUTE: Stage 5C.2G-R validity analysis is not authorized")
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/stage5c2gR/exact_mobile_benchmark.yaml")
    parser.add_argument("--protocol", default="configs/stage5c2gR/protocol.yaml")
    parser.add_argument("--validation", default="results/stage5c2gR/validation")
    parser.add_argument("--out", default="results/stage5c2gR/validity_analysis")
    args = parser.parse_args()
    protocol_lock = assert_protocol_locked(protocol_path=args.protocol)
    mapping = checked_lock("results/stage5c2gR/mobility_mapping/LOCKED.json", "PASSED_AND_FROZEN", protocol_lock)
    tolerance = checked_lock("results/stage5c2gR/validity_tolerances/LOCKED.json", "CALIBRATION_PASSED_AND_TOLERANCES_FROZEN", protocol_lock)
    benchmark = load_yaml(args.config)["stage5c2gR_exact_benchmark"]
    protocol = load_yaml(args.protocol)["stage5c2gR_protocol"]
    root = ROOT / args.validation
    manifest = json.loads((root / "stage5c2gR_manifest.json").read_text(encoding="utf-8"))
    if not manifest.get("all_attempts_completed") or manifest.get("tolerance_lock_sha256") != tolerance["lock_sha256"]:
        raise RuntimeError("validation manifest is incomplete or not bound to the passed calibration lock")
    exact = pd.read_csv(root / "stage5c2gR_exact_curves.csv")
    surrogate = pd.read_csv(root / "stage5c2gR_surrogate_curves.csv")
    density = pd.read_csv(root / "stage5c2gR_hole_density.csv")
    configurations = pd.read_csv(root / "stage5c2gR_hole_configuration_history.csv", keep_default_na=False)
    designated = {case["id"]: bool(case.get("designated_confirmatory")) for case in benchmark["validation_cases"]}
    fixed_time = float(benchmark["fixed_time"])
    near_tie = float(tolerance["ranking_near_tie_tolerance_db"])
    comparison_rows, contrast_rows, local_rows, transport_rows = [], [], [], []

    for case_id, is_designated in designated.items():
        for occupancy_idx in sorted(exact.loc[exact.case_id == case_id, "occupancy_idx"].unique()):
            exact_occ = exact[(exact.case_id == case_id) & (exact.occupancy_idx == occupancy_idx)]
            surrogate_occ = surrogate[(surrogate.case_id == case_id) & (surrogate.occupancy_idx == occupancy_idx)]
            exact_effects, surrogate_effects = {}, {}
            for label in benchmark["labels"]:
                exact_curve = exact_occ[exact_occ.label == label].groupby("time", as_index=False).xi2_db.mean()
                surrogate_curve = surrogate_occ[surrogate_occ.label == label].groupby("time", as_index=False).xi2_db.mean()
                correlation, rmse = curve_metrics(exact_curve, surrogate_curve)
                comparison_rows.append({"case_id": case_id, "occupancy_idx": int(occupancy_idx), "label": label, "correlation": correlation, "rmse_db": rmse, "correlation_pass": bool(correlation >= float(tolerance["minimum_time_profile_correlation"])), "rmse_pass": bool(rmse <= float(tolerance["maximum_validation_rmse_db"])), "designated_confirmatory": is_designated})
            exact_static = value_at(exact_occ[exact_occ.label == "static_only"].groupby("time", as_index=False).xi2_db.mean(), fixed_time)
            surrogate_static = value_at(surrogate_occ[surrogate_occ.label == "static_only"].groupby("time", as_index=False).xi2_db.mean(), fixed_time)
            for label in ["mobile_only", "spin_density_only", "combined"]:
                exact_effects[label] = exact_static - value_at(exact_occ[exact_occ.label == label].groupby("time", as_index=False).xi2_db.mean(), fixed_time)
                surrogate_effects[label] = surrogate_static - value_at(surrogate_occ[surrogate_occ.label == label].groupby("time", as_index=False).xi2_db.mean(), fixed_time)
                contrast_rows.append({"case_id": case_id, "occupancy_idx": int(occupancy_idx), "label": label, "exact_effect_db": exact_effects[label], "surrogate_effect_db": surrogate_effects[label], "sign_agreement": bool(np.sign(exact_effects[label]) == np.sign(surrogate_effects[label])), "designated_confirmatory": is_designated})
            ranking_pass = ranking_agrees(exact_effects, surrogate_effects, near_tie)
            for row in contrast_rows:
                if row["case_id"] == case_id and row["occupancy_idx"] == occupancy_idx: row["component_ranking_agreement"] = ranking_pass
            for offset in benchmark["local_window_offsets"]:
                target = fixed_time + float(offset)
                exact_effect = value_at(exact_occ[exact_occ.label == "static_only"].groupby("time", as_index=False).xi2_db.mean(), target) - value_at(exact_occ[exact_occ.label == "combined"].groupby("time", as_index=False).xi2_db.mean(), target)
                surrogate_effect = value_at(surrogate_occ[surrogate_occ.label == "static_only"].groupby("time", as_index=False).xi2_db.mean(), target) - value_at(surrogate_occ[surrogate_occ.label == "combined"].groupby("time", as_index=False).xi2_db.mean(), target)
                local_rows.append({"case_id": case_id, "occupancy_idx": int(occupancy_idx), "offset": float(offset), "exact_effect_db": exact_effect, "surrogate_effect_db": surrogate_effect, "sign_agreement": bool(np.sign(exact_effect) == np.sign(surrogate_effect)), "designated_confirmatory": is_designated})

            shape = tuple(int(value) for value in str(exact_occ.iloc[0]["shape"]).split("x"))
            graph = hypercubic_lattice(shape, False)
            holes = [int(value) for value in str(exact_occ.iloc[0].initial_holes).split(";")]
            for label in ["mobile_only", "combined"]:
                exact_density = density[(density.case_id == case_id) & (density.occupancy_idx == occupancy_idx) & (density.label == label) & (density.method == "exact")].groupby(["time", "site"]).hole_density.mean().unstack().to_numpy(float)
                surrogate_density = density[(density.case_id == case_id) & (density.occupancy_idx == occupancy_idx) & (density.label == label) & (density.method == "surrogate")].groupby(["time", "site"]).hole_density.mean().unstack().to_numpy(float)
                discrepancy = transport_discrepancy(exact_density, surrogate_density, graph.coords, holes, configuration_distribution(configurations, case_id, occupancy_idx, label, "exact"), configuration_distribution(configurations, case_id, occupancy_idx, label, "surrogate"))
                transport_rows.append({"case_id": case_id, "occupancy_idx": int(occupancy_idx), "label": label, "density_l1_mean": float(np.mean(discrepancy["density_l1_by_time"])), "normalized_msd_rmse": float(np.sqrt(np.mean(np.asarray(discrepancy["normalized_msd_error"]) ** 2))), "return_probability_rmse": float(np.sqrt(np.mean(np.asarray(discrepancy["return_probability_error"]) ** 2))), "configuration_tv_mean": float(np.mean(discrepancy["configuration_tv_by_time"])), "designated_confirmatory": is_designated})

    comparisons = pd.DataFrame(comparison_rows); contrasts = pd.DataFrame(contrast_rows); local = pd.DataFrame(local_rows); transport = pd.DataFrame(transport_rows)
    transport["passed"] = (transport.density_l1_mean <= float(protocol["transport_mapping_gates"]["density_l1_mean_maximum"])) & (transport.normalized_msd_rmse <= float(protocol["transport_mapping_gates"]["normalized_msd_rmse_maximum"])) & (transport.return_probability_rmse <= float(protocol["transport_mapping_gates"]["return_probability_rmse_maximum"])) & (transport.configuration_tv_mean <= float(protocol["transport_mapping_gates"]["configuration_tv_mean_maximum"]))
    expected_particles = exact["shape"].str.split("x").apply(lambda values: int(np.prod([int(value) for value in values]))) - exact.n_holes.astype(int)
    accounting = {"max_norm_error": float(exact.norm_error.max()), "max_particle_number_error": float(np.max(np.abs(exact.particle_number - expected_particles))), "max_hole_number_error": float(np.max(np.abs(exact.hole_number_expectation - exact.n_holes))), "max_hamiltonian_hermiticity_error": float(exact.hamiltonian_hermiticity_error.max())}
    designated_comparisons = comparisons[comparisons.designated_confirmatory]; designated_contrasts = contrasts[contrasts.designated_confirmatory]; designated_local = local[local.designated_confirmatory]; designated_transport = transport[transport.designated_confirmatory]
    gate = {"stage": "stage5c2gR_untouched_validity_gate", "protocol_candidate_sha256": protocol_lock["candidate_sha256"], "mapping_lock_sha256": mapping["lock_sha256"], "tolerance_lock_sha256": tolerance["lock_sha256"], "time_profile_and_rmse_pass": bool(designated_comparisons.correlation_pass.all() and designated_comparisons.rmse_pass.all()), "sign_agreement_pass": bool(designated_contrasts.sign_agreement.all()), "component_ranking_agreement_pass": bool(designated_contrasts.component_ranking_agreement.all()), "local_window_sign_pass": bool(designated_local.sign_agreement.all()), "transport_pass": bool(designated_transport.passed.all()), "exact_accounting_pass": bool(all(value <= 1e-10 for value in accounting.values())), "accounting": accounting, "hierarchical_units_reported": True}
    gate["passed"] = bool(all(gate[key] for key in ["time_profile_and_rmse_pass", "sign_agreement_pass", "component_ranking_agreement_pass", "local_window_sign_pass", "transport_pass", "exact_accounting_pass"]))
    gate["gate_sha256"] = sha256_payload(gate)
    output = ROOT / args.out; output.mkdir(parents=True, exist_ok=True)
    comparisons.to_csv(output / "time_profile_metrics.csv", index=False); contrasts.to_csv(output / "component_contrasts.csv", index=False); local.to_csv(output / "local_window_signs.csv", index=False); transport.to_csv(output / "transport_metrics.csv", index=False)
    (output / "stage5c2gR_validity_gate.json").write_text(json.dumps(gate, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(gate, indent=2))
    if not gate["passed"]: raise SystemExit("untouched validity failed; fixed-hole production remains blocked")


if __name__ == "__main__":
    main()
