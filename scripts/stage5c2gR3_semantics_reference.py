from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from stage5c2gR3_common import plan_g1, sha256_payload


def _absolute_sanity_reference(frame: pd.DataFrame, method: str, planned: dict, stage: dict) -> dict:
    rules = stage["absolute_sanity"]
    case = next(value for value in stage["cases"] if str(value["id"]) == str(planned["case_id"]))
    sites = int(np.prod([int(value) for value in case["shape"]]))
    holes = len(case["holes"])
    particles = sites - holes
    sx, sy, sz = (frame[name].to_numpy(dtype=float) for name in ["Sx", "Sy", "Sz"])
    length_squared = sx * sx + sy * sy + sz * sz
    xi = frame["xi2"].to_numpy(dtype=float)
    variance = frame["min_var"].to_numpy(dtype=float)
    db = frame["xi2_db"].to_numpy(dtype=float)
    bound = particles / 2.0 + float(rules["collective_component_abs_margin"])
    spin_interval = tuple(float(value) for value in rules["spin_length_range"])
    xi_interval = tuple(float(value) for value in rules["xi2_range"])
    with np.errstate(divide="ignore", invalid="ignore"):
        derived_db = 10.0 * np.log10(xi)
        derived_xi = particles * variance / length_squared
    checks = {
        "initial_sx": abs(float(sx[0]) - particles / 2.0) <= float(rules["time_zero_exact_abs_tolerance"] if method == "exact" else rules["time_zero_surrogate_sx_abs_tolerance"]),
        "collective_component_bounds": bool(max(np.max(np.abs(sx)), np.max(np.abs(sy)), np.max(np.abs(sz))) <= bound),
        "spin_length_bounds": bool(frame["spin_length"].between(spin_interval[0], spin_interval[1], inclusive="both").all()),
        "xi2_bounds": bool(pd.Series(xi).between(xi_interval[0], xi_interval[1], inclusive="both").all()),
        "minimum_variance_bounds": bool(pd.Series(variance).between(0.0, float(rules["min_variance_abs_max_factor"]) * particles * particles, inclusive="both").all()),
        "xi2_db_identity": bool(np.max(np.abs(db - derived_db)) <= float(rules["xi2_db_consistency_abs_tolerance"])),
        "wineland_identity": bool(np.max(np.abs(xi - derived_xi)) <= float(rules["wineland_identity_abs_tolerance"])),
    }
    if method == "exact":
        zero_tolerance = float(rules["time_zero_exact_abs_tolerance"])
        checks.update({
            "initial_sy_sz": abs(float(sy[0])) <= zero_tolerance and abs(float(sz[0])) <= zero_tolerance,
            "initial_css": abs(float(xi[0]) - 1.0) <= zero_tolerance and abs(float(db[0])) <= zero_tolerance and abs(float(variance[0]) - particles / 4.0) <= zero_tolerance and abs(float(frame["spin_length"].iloc[0]) - 1.0) <= zero_tolerance,
            "particle_count": bool(np.max(np.abs(frame["particle_number"].to_numpy(dtype=float) - particles)) <= float(rules["count_abs_tolerance"])),
            "hole_count": bool(np.max(np.abs(frame["hole_number_expectation"].to_numpy(dtype=float) - holes)) <= float(rules["count_abs_tolerance"])),
            "norm": bool(np.max(np.abs(frame["norm_error"].to_numpy(dtype=float))) <= float(rules["norm_error_max"])),
        })
    else:
        xi_window = tuple(float(value) for value in rules["time_zero_surrogate_xi2_range"])
        spin_window = tuple(float(value) for value in rules["time_zero_surrogate_spin_length_range"])
        bonds = sum((int(extent) - 1) * int(sites / int(extent)) for extent in case["shape"])
        active = frame["active_bonds"].to_numpy(dtype=float)
        checks.update({
            "initial_css_window": xi_window[0] <= float(xi[0]) <= xi_window[1] and spin_window[0] <= float(frame["spin_length"].iloc[0]) <= spin_window[1],
            "particle_count": bool(np.max(np.abs(frame["N_eff"].to_numpy(dtype=float) - particles)) <= float(rules["count_abs_tolerance"])),
            "active_bonds": bool(np.all((active >= 0.0) & (active <= bonds)) and np.max(np.abs(active - np.round(active))) <= float(rules["count_abs_tolerance"])),
            "hole_spin_covariance": bool(np.max(np.abs(frame["hole_spin_covariance"].to_numpy(dtype=float))) <= 1.0 + float(rules["collective_component_abs_margin"])),
        })
    change = max(float((frame[name].astype(float) - float(frame[name].iloc[0])).abs().max()) for name in rules["nontrivial_columns"])
    checks["nontrivial_dynamics"] = change >= float(rules["minimum_nontrivial_time_change"])
    return {"checks": checks, "maximum_nontrivial_time_change": change, "passed": all(checks.values())}


def derive_g1_decision_reference(curves_path: str | Path, registry_path: str | Path, config: dict) -> dict:
    """Independent merge-based implementation used to cross-check the primary verifier."""
    stage = config["stage5c2gR3_G1"]
    plan_frame = pd.DataFrame(plan_g1(config)).sort_values("comparison_id", kind="mergesort")
    registry = pd.read_csv(registry_path, dtype={"comparison_id": str}).sort_values("comparison_id", kind="mergesort")
    identity_columns = ["comparison_id", "case_id", "method", "static_label", "comparison_label", "occupancy_idx", "path_idx", "phase_idx", "block_id", "occupancy_realization_id", "hole_path_realization_id", "phase_batch_realization_id", "exact_initial_state_id", "occupancy_seed", "hole_path_seed", "phase_batch_seed"]
    if not registry[identity_columns].astype(str).reset_index(drop=True).equals(plan_frame[identity_columns].astype(str).reset_index(drop=True)):
        raise RuntimeError("reference semantic verifier rejected registry identity")
    curves = pd.read_csv(curves_path, dtype={"comparison_id": str})
    expected_times = np.linspace(float(stage["times"]["start"]), float(stage["times"]["stop"]), int(stage["times"]["points"]))
    # Independently allow only binary64/CSV serialization noise in the time
    # coordinate.  This is deliberately unrelated to the scientific equality
    # tolerance applied to observable curves.
    time_atol = 8.0 * np.finfo(np.float64).eps * max(1.0, float(np.max(np.abs(expected_times))))
    tolerance = float(stage["tolerance_max_abs_full_curve_difference"])
    rows = []
    for planned in plan_frame.to_dict("records"):
        cid, method = str(planned["comparison_id"]), str(planned["method"])
        columns = [str(value) for value in stage["method_value_columns"][method]]
        subset = curves[(curves.comparison_id.astype(str) == cid) & (curves.method.astype(str) == method)]
        left = subset[subset.label.astype(str) == str(planned["static_label"])][["time", *columns]].copy()
        right = subset[subset.label.astype(str) == str(planned["comparison_label"])][["time", *columns]].copy()
        paired = left.merge(right, on="time", how="outer", validate="one_to_one", suffixes=("_a", "_b"), indicator=True).sort_values("time")
        if len(paired) != len(expected_times) or not (paired._merge == "both").all() or not np.allclose(
            paired.time.to_numpy(float), expected_times, rtol=0.0, atol=time_atol
        ):
            raise RuntimeError(f"reference semantic verifier rejected time pairing: {cid}")
        differences = np.concatenate([np.abs(paired[f"{column}_a"].to_numpy(float) - paired[f"{column}_b"].to_numpy(float)) for column in columns])
        if not np.isfinite(differences).all():
            raise RuntimeError(f"reference semantic verifier rejected non-finite values: {cid}")
        maximum = float(differences.max())
        sanity_by_label = {}
        for label in [str(planned["static_label"]), str(planned["comparison_label"])]:
            sanity_frame = subset[subset.label.astype(str) == label].sort_values("time", kind="mergesort")
            sanity_by_label[label] = _absolute_sanity_reference(sanity_frame, method, planned, stage)
        equality_pass = bool(maximum <= tolerance)
        absolute_pass = all(value["passed"] for value in sanity_by_label.values())
        rows.append({"comparison_id": cid, "max_abs_full_curve_difference": maximum, "tolerance": tolerance, "equality_pass": equality_pass, "absolute_sanity": sanity_by_label, "absolute_sanity_pass": absolute_pass, "derived_pass": equality_pass and absolute_pass})
    rows.sort(key=lambda row: row["comparison_id"])
    payload = {"schema_version": stage["schema_version"], "derivation": "paired_equality_and_absolute_physical_sanity_reference_v2", "rows": rows, "maximum_difference": max(row["max_abs_full_curve_difference"] for row in rows), "equality_passed": all(row["equality_pass"] for row in rows), "absolute_sanity_passed": all(row["absolute_sanity_pass"] for row in rows), "passed": all(row["derived_pass"] for row in rows)}
    payload["decision_sha256"] = sha256_payload(payload)
    return payload


def assert_semantic_agreement(primary: dict, reference: dict) -> None:
    keys = ["rows", "maximum_difference", "equality_passed", "absolute_sanity_passed", "passed", "schema_version"]
    if any(primary[key] != reference[key] for key in keys):
        raise RuntimeError("independent G1 semantic verifiers disagree")
