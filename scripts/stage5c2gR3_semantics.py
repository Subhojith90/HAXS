from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

from stage5c2gR3_common import plan_g1, sha256_payload


def _case_by_id(stage: dict) -> dict[str, dict]:
    return {str(case["id"]): case for case in stage["cases"]}


def _absolute_sanity_primary(frame: pd.DataFrame, method: str, planned: dict, stage: dict) -> dict:
    sanity = stage["absolute_sanity"]
    case = _case_by_id(stage)[str(planned["case_id"])]
    n_sites = int(np.prod(np.asarray(case["shape"], dtype=int)))
    n_holes = len(case["holes"])
    n_particles = n_sites - n_holes
    components = frame[["Sx", "Sy", "Sz"]].to_numpy(float)
    spin_norm2 = np.sum(components * components, axis=1)
    xi2 = frame["xi2"].to_numpy(float)
    min_var = frame["min_var"].to_numpy(float)
    reported_db = frame["xi2_db"].to_numpy(float)
    # Adversarial fixtures intentionally include zero and nonsensical curves.
    # Derive their failed identities without emitting thousands of numerical
    # warnings; non-finite derived values still make the checks fail closed.
    with np.errstate(divide="ignore", invalid="ignore"):
        derived_db = 10.0 * np.log10(xi2)
        derived_xi2 = n_particles * min_var / spin_norm2
    component_bound = n_particles / 2.0 + float(sanity["collective_component_abs_margin"])
    spin_lo, spin_hi = map(float, sanity["spin_length_range"])
    xi2_lo, xi2_hi = map(float, sanity["xi2_range"])
    checks = {
        "initial_sx": abs(float(frame["Sx"].iloc[0]) - n_particles / 2.0) <= float(sanity["time_zero_exact_abs_tolerance"] if method == "exact" else sanity["time_zero_surrogate_sx_abs_tolerance"]),
        "collective_component_bounds": bool(np.all(np.abs(components) <= component_bound)),
        "spin_length_bounds": bool(np.all((frame["spin_length"].to_numpy(float) >= spin_lo) & (frame["spin_length"].to_numpy(float) <= spin_hi))),
        "xi2_bounds": bool(np.all((xi2 >= xi2_lo) & (xi2 <= xi2_hi))),
        "minimum_variance_bounds": bool(np.all((min_var >= 0.0) & (min_var <= float(sanity["min_variance_abs_max_factor"]) * n_particles * n_particles))),
        "xi2_db_identity": bool(np.max(np.abs(reported_db - derived_db)) <= float(sanity["xi2_db_consistency_abs_tolerance"])),
        "wineland_identity": bool(np.max(np.abs(xi2 - derived_xi2)) <= float(sanity["wineland_identity_abs_tolerance"])),
    }
    if method == "exact":
        atol = float(sanity["time_zero_exact_abs_tolerance"])
        checks.update({
            "initial_sy_sz": abs(float(frame["Sy"].iloc[0])) <= atol and abs(float(frame["Sz"].iloc[0])) <= atol,
            "initial_css": abs(float(xi2[0]) - 1.0) <= atol and abs(float(reported_db[0])) <= atol and abs(float(min_var[0]) - n_particles / 4.0) <= atol and abs(float(frame["spin_length"].iloc[0]) - 1.0) <= atol,
            "particle_count": bool(np.max(np.abs(frame["particle_number"].to_numpy(float) - n_particles)) <= float(sanity["count_abs_tolerance"])),
            "hole_count": bool(np.max(np.abs(frame["hole_number_expectation"].to_numpy(float) - n_holes)) <= float(sanity["count_abs_tolerance"])),
            "norm": bool(np.max(np.abs(frame["norm_error"].to_numpy(float))) <= float(sanity["norm_error_max"])),
        })
    else:
        initial_xi_lo, initial_xi_hi = map(float, sanity["time_zero_surrogate_xi2_range"])
        initial_spin_lo, initial_spin_hi = map(float, sanity["time_zero_surrogate_spin_length_range"])
        max_bonds = sum((int(size) - 1) * int(n_sites / int(size)) for size in case["shape"])
        active_bonds = frame["active_bonds"].to_numpy(float)
        checks.update({
            "initial_css_window": initial_xi_lo <= float(xi2[0]) <= initial_xi_hi and initial_spin_lo <= float(frame["spin_length"].iloc[0]) <= initial_spin_hi,
            "particle_count": bool(np.max(np.abs(frame["N_eff"].to_numpy(float) - n_particles)) <= float(sanity["count_abs_tolerance"])),
            "active_bonds": bool(np.all((active_bonds >= 0.0) & (active_bonds <= max_bonds) & (np.abs(active_bonds - np.rint(active_bonds)) <= float(sanity["count_abs_tolerance"])))),
            "hole_spin_covariance": bool(np.all(np.abs(frame["hole_spin_covariance"].to_numpy(float)) <= 1.0 + float(sanity["collective_component_abs_margin"]))),
        })
    nontrivial = max(float(np.max(np.abs(frame[column].to_numpy(float) - float(frame[column].iloc[0])))) for column in sanity["nontrivial_columns"])
    checks["nontrivial_dynamics"] = nontrivial >= float(sanity["minimum_nontrivial_time_change"])
    return {"checks": checks, "maximum_nontrivial_time_change": nontrivial, "passed": all(checks.values())}


def derive_g1_decision(curves_path: str | Path, registry_path: str | Path, config: dict) -> dict:
    """Primary semantic verifier. Stored comparison differences/pass flags are never read."""
    stage = config["stage5c2gR3_G1"]
    plan = plan_g1(config)
    registry = pd.read_csv(registry_path, dtype={"comparison_id": str})
    curves = pd.read_csv(curves_path, dtype={"comparison_id": str})
    expected_ids = [str(row["comparison_id"]) for row in plan]
    observed_ids = registry["comparison_id"].astype(str).tolist()
    if sorted(observed_ids) != sorted(expected_ids) or len(observed_ids) != len(set(observed_ids)):
        raise RuntimeError("G1 registry does not equal the unique canonical comparison plan")
    identity_columns = ["comparison_id", "case_id", "method", "static_label", "comparison_label", "occupancy_idx", "path_idx", "phase_idx", "block_id", "occupancy_realization_id", "hole_path_realization_id", "phase_batch_realization_id", "exact_initial_state_id", "occupancy_seed", "hole_path_seed", "phase_batch_seed"]
    canonical_registry = pd.DataFrame(plan)[identity_columns].sort_values("comparison_id", kind="mergesort").astype(str).reset_index(drop=True)
    observed_registry = registry[identity_columns].sort_values("comparison_id", kind="mergesort").astype(str).reset_index(drop=True)
    if not observed_registry.equals(canonical_registry):
        raise RuntimeError("G1 registry fields differ from the canonical comparison plan")
    if set(registry.columns) != set(identity_columns):
        raise RuntimeError("G1 registry schema differs from the golden canonical schema")
    expected_curve_columns = {"schema_version", "comparison_id", "label", "method", "time"}
    for columns in stage["method_value_columns"].values():
        expected_curve_columns.update(str(column) for column in columns)
    if set(curves.columns) != expected_curve_columns:
        raise RuntimeError("G1 raw curve columns differ from the golden canonical schema")
    if len(curves) != int(stage["expected_curve_rows"]):
        raise RuntimeError("G1 raw curve row count differs from canonical schema")
    if "schema_version" not in curves or set(curves["schema_version"].astype(str)) != {str(stage["schema_version"])}:
        raise RuntimeError("G1 raw curve schema version failed")
    expected_times = np.linspace(float(stage["times"]["start"]), float(stage["times"]["stop"]), int(stage["times"]["points"]))
    # CSV decimal round-tripping can move a binary64 value by one ULP.  Accept
    # only that serialization noise; scientific curve tolerances remain
    # separate and are applied below to the observable values.
    time_atol = 8.0 * np.finfo(np.float64).eps * max(1.0, float(np.max(np.abs(expected_times))))
    tolerance = float(stage["tolerance_max_abs_full_curve_difference"])
    decisions = []
    for planned in plan:
        comparison_id = str(planned["comparison_id"])
        subset = curves[curves["comparison_id"].astype(str) == comparison_id]
        method = str(planned["method"])
        labels = [str(planned["static_label"]), str(planned["comparison_label"])]
        if set(subset["method"].astype(str)) != {method} or set(subset["label"].astype(str)) != set(labels):
            raise RuntimeError(f"G1 curve method/label identity failed: {comparison_id}")
        value_columns = [str(value) for value in stage["method_value_columns"][method]]
        arrays = {}
        sanity_by_label = {}
        for label in labels:
            frame = subset[subset["label"].astype(str) == label].sort_values("time", kind="mergesort")
            if len(frame) != len(expected_times) or not np.allclose(
                frame["time"].to_numpy(float), expected_times, rtol=0.0, atol=time_atol
            ):
                raise RuntimeError(f"G1 canonical time grid failed: {comparison_id}/{label}")
            if any(column not in frame for column in value_columns):
                raise RuntimeError(f"G1 semantic schema column missing: {comparison_id}/{label}")
            values = frame[value_columns].to_numpy(float)
            if not np.isfinite(values).all():
                raise RuntimeError(f"G1 non-finite raw curve: {comparison_id}/{label}")
            arrays[label] = values
            sanity_by_label[label] = _absolute_sanity_primary(frame, method, planned, stage)
        difference = float(np.max(np.abs(arrays[labels[0]] - arrays[labels[1]])))
        equality_pass = bool(difference <= tolerance)
        absolute_pass = all(value["passed"] for value in sanity_by_label.values())
        decisions.append({"comparison_id": comparison_id, "max_abs_full_curve_difference": difference, "tolerance": tolerance, "equality_pass": equality_pass, "absolute_sanity": sanity_by_label, "absolute_sanity_pass": absolute_pass, "derived_pass": equality_pass and absolute_pass})
    decisions.sort(key=lambda row: row["comparison_id"])
    if len(decisions) != int(stage["expected_comparison_rows"]):
        raise RuntimeError("G1 derived decision row count failed")
    payload = {
        "schema_version": stage["schema_version"],
        "derivation": "paired_equality_and_absolute_physical_sanity_primary_v2",
        "rows": decisions,
        "maximum_difference": max(row["max_abs_full_curve_difference"] for row in decisions),
        "equality_passed": all(row["equality_pass"] for row in decisions),
        "absolute_sanity_passed": all(row["absolute_sanity_pass"] for row in decisions),
        "passed": all(row["derived_pass"] for row in decisions),
    }
    payload["decision_sha256"] = sha256_payload(payload)
    return payload
