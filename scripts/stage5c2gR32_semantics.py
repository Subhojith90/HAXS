from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from stage5c2gR32_common import sha256_payload


def _cases(stage: dict) -> dict[str, dict]:
    return {str(case["id"]): case for case in stage["cases"]}


def _particle_count(case: dict, occupancy_id: str) -> int:
    occupancy = next(
        value
        for value in case["occupancies"]
        if str(value["occupancy_id"]) == str(occupancy_id)
    )
    return int(np.prod(case["shape"])) - len(occupancy["holes"])


def _curve_sanity(frame: pd.DataFrame, method: str, n_particles: int, margin: float) -> dict:
    components = frame[["Sx", "Sy", "Sz"]].to_numpy(float)
    xi2 = frame["xi2"].to_numpy(float)
    xi2_db = frame["xi2_db"].to_numpy(float)
    min_var = frame["min_var"].to_numpy(float)
    spin_norm2 = np.sum(components * components, axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        derived_db = 10.0 * np.log10(xi2)
        derived_xi2 = n_particles * min_var / spin_norm2
    checks = {
        "finite": bool(
            np.isfinite(frame.select_dtypes(include=[np.number]).to_numpy(float)).all()
        ),
        "collective_component_bounds": bool(
            np.all(np.abs(components) <= n_particles / 2.0 + margin)
        ),
        "initial_sx": abs(float(frame["Sx"].iloc[0]) - n_particles / 2.0) <= margin,
        "xi2_positive": bool(np.all(xi2 > 0.0)),
        "minimum_variance_nonnegative": bool(np.all(min_var >= 0.0)),
        "xi2_db_identity": bool(np.max(np.abs(xi2_db - derived_db)) <= 1.0e-9),
        "wineland_identity": bool(np.max(np.abs(xi2 - derived_xi2)) <= 1.0e-8),
        "spin_length_bounds": bool(frame["spin_length"].between(0.05, 1.01).all()),
        "nontrivial_dynamics": bool(
            max(
                np.max(np.abs(frame[column].to_numpy(float) - frame[column].iloc[0]))
                for column in ["Sx", "xi2", "min_var"]
            )
            >= 1.0e-6
        ),
    }
    if method == "surrogate":
        checks.update(
            {
                "particle_count": bool(
                    np.max(
                        np.abs(frame["N_eff"].to_numpy(float) - float(n_particles))
                    )
                    <= margin
                ),
                "initial_css": bool(
                    0.50 <= float(xi2[0]) <= 1.50
                    and 0.95 <= float(frame["spin_length"].iloc[0]) <= 1.01
                ),
            }
        )
    else:
        checks.update(
            {
                "particle_count": bool(
                    np.max(
                        np.abs(
                            frame["particle_number"].to_numpy(float)
                            - float(n_particles)
                        )
                    )
                    <= margin
                ),
                "initial_css": bool(
                    abs(float(xi2[0]) - 1.0) <= margin
                    and abs(float(xi2_db[0])) <= margin
                    and abs(float(min_var[0]) - n_particles / 4.0) <= margin
                ),
                "norm": bool(
                    np.max(np.abs(frame["norm_error"].to_numpy(float))) <= margin
                ),
            }
        )
    return {"checks": checks, "passed": all(checks.values())}


def _expected_units(stage: dict) -> list[dict]:
    units = []
    for case in stage["cases"]:
        for occupancy in case["occupancies"]:
            for substeps in stage["integration_substeps"]:
                for method in ["exact", "surrogate"]:
                    units.append(
                        {
                            "case_id": str(case["id"]),
                            "occupancy_id": str(occupancy["occupancy_id"]),
                            "substeps": int(substeps),
                            "method": method,
                            "labels": list(map(str, case["labels"])),
                        }
                    )
    return units


def derive_quadrature_decision(
    surrogate_curves_path: str | Path,
    exact_curves_path: str | Path,
    node_registry_path: str | Path,
    config: dict,
) -> dict:
    stage = config["stage5c2gR32_G1"]
    surrogate = pd.read_csv(surrogate_curves_path)
    exact = pd.read_csv(exact_curves_path)
    nodes = pd.read_csv(node_registry_path)
    if len(nodes) != int(stage["expected_quadrature_registry_rows"]):
        raise RuntimeError("quadrature registry row count differs from frozen plan")
    if nodes["node_id"].duplicated().any():
        raise RuntimeError("quadrature registry contains duplicate node IDs")
    expected_nodes = int(stage["quadrature"]["expected_nodes_per_unit"])
    for _, group in nodes.groupby(["case_id", "occupancy_id"], sort=True):
        if len(group) != expected_nodes:
            raise RuntimeError("quadrature unit is incomplete")
        if sorted(group["node_index"].astype(int)) != list(range(expected_nodes)):
            raise RuntimeError("quadrature node ordering or completeness failed")
        if abs(float(group["weight"].sum()) - 1.0) > 1.0e-12:
            raise RuntimeError("quadrature weights do not sum to one")
        if group["phase_code"].astype(str).nunique() != expected_nodes:
            raise RuntimeError("quadrature phase codes are not unique")
    if len(surrogate) != int(stage["expected_weighted_curve_rows"]):
        raise RuntimeError("weighted surrogate curve row count failed")
    if len(exact) != int(stage["expected_exact_curve_rows"]):
        raise RuntimeError("matched exact curve row count failed")

    margin = float(stage["numerical_roundoff_margin"])
    tolerance = float(stage["tolerance_max_abs_full_curve_difference"])
    cases = _cases(stage)
    rows = []
    for unit in _expected_units(stage):
        source = exact if unit["method"] == "exact" else surrogate
        subset = source[
            (source["case_id"].astype(str) == unit["case_id"])
            & (source["occupancy_id"].astype(str) == unit["occupancy_id"])
            & (source["substeps"].astype(int) == unit["substeps"])
            & (source["method"].astype(str) == unit["method"])
        ]
        labels = unit["labels"]
        left = subset[subset["label"].astype(str) == labels[0]].sort_values("time")
        right = subset[subset["label"].astype(str) == labels[1]].sort_values("time")
        if len(left) != int(stage["times"]["points"]) or len(right) != len(left):
            raise RuntimeError(f"incomplete curve unit: {unit}")
        columns = [
            column
            for column in left.columns
            if column
            not in {
                "schema_version",
                "case_id",
                "occupancy_id",
                "substeps",
                "method",
                "label",
            }
        ]
        numeric_columns = [column for column in columns if column != "time"]
        maximum = float(
            np.max(
                np.abs(
                    left[numeric_columns].to_numpy(float)
                    - right[numeric_columns].to_numpy(float)
                )
            )
        )
        particles = _particle_count(cases[unit["case_id"]], unit["occupancy_id"])
        sanity = {
            labels[0]: _curve_sanity(left, unit["method"], particles, margin),
            labels[1]: _curve_sanity(right, unit["method"], particles, margin),
        }
        rows.append(
            {
                **{key: unit[key] for key in ["case_id", "occupancy_id", "substeps", "method"]},
                "labels": labels,
                "maximum_difference": maximum,
                "equality_pass": maximum <= tolerance,
                "sanity": sanity,
                "sanity_pass": all(value["passed"] for value in sanity.values()),
            }
        )

    payload = {
        "schema_version": stage["schema_version"],
        "derivation": "stage5c2gR32_deterministic_quadrature_primary_v1",
        "rows": rows,
        "node_registry_pass": True,
        "maximum_difference": max(row["maximum_difference"] for row in rows),
        "equality_passed": all(row["equality_pass"] for row in rows),
        "absolute_sanity_passed": all(row["sanity_pass"] for row in rows),
    }
    payload["passed"] = (
        payload["node_registry_pass"]
        and payload["equality_passed"]
        and payload["absolute_sanity_passed"]
    )
    payload["decision_sha256"] = sha256_payload(payload)
    return payload


def derive_quadrature_decision_reference(
    surrogate_curves_path: str | Path,
    exact_curves_path: str | Path,
    node_registry_path: str | Path,
    config: dict,
) -> dict:
    stage = config["stage5c2gR32_G1"]
    sources = {
        "surrogate": pd.read_csv(surrogate_curves_path),
        "exact": pd.read_csv(exact_curves_path),
    }
    nodes = pd.read_csv(node_registry_path, dtype={"phase_code": str})
    expected_nodes = int(stage["quadrature"]["expected_nodes_per_unit"])
    node_groups = list(nodes.groupby(["case_id", "occupancy_id"], sort=True))
    node_pass = (
        len(nodes) == int(stage["expected_quadrature_registry_rows"])
        and not nodes["node_id"].duplicated().any()
        and all(
            len(group) == expected_nodes
            and set(group["node_index"].astype(int)) == set(range(expected_nodes))
            and len(set(group["phase_code"].astype(str))) == expected_nodes
            and abs(float(group["weight"].sum()) - 1.0) <= 1.0e-12
            for _, group in node_groups
        )
    )
    if not node_pass:
        raise RuntimeError("reference quadrature registry verification failed")
    cases = _cases(stage)
    tolerance = float(stage["tolerance_max_abs_full_curve_difference"])
    margin = float(stage["numerical_roundoff_margin"])
    rows = []
    for unit in _expected_units(stage):
        source = sources[unit["method"]]
        selected = source[
            (source.case_id.astype(str) == unit["case_id"])
            & (source.occupancy_id.astype(str) == unit["occupancy_id"])
            & (source.substeps.astype(int) == unit["substeps"])
            & (source.method.astype(str) == unit["method"])
        ].copy()
        labels = unit["labels"]
        identity = {
            "schema_version",
            "case_id",
            "occupancy_id",
            "substeps",
            "method",
            "label",
            "time",
        }
        values = [column for column in selected.columns if column not in identity]
        left = selected[selected.label.astype(str) == labels[0]].sort_values("time")
        right = selected[selected.label.astype(str) == labels[1]].sort_values("time")
        paired = left[["time", *values]].merge(
            right[["time", *values]],
            on="time",
            how="outer",
            validate="one_to_one",
            suffixes=("_left", "_right"),
            indicator=True,
        )
        if (
            len(paired) != int(stage["times"]["points"])
            or not (paired["_merge"] == "both").all()
        ):
            raise RuntimeError(f"reference curve pairing failed: {unit}")
        difference = max(
            float(
                np.max(
                    np.abs(
                        paired[f"{column}_left"].to_numpy(float)
                        - paired[f"{column}_right"].to_numpy(float)
                    )
                )
            )
            for column in values
        )
        particles = _particle_count(cases[unit["case_id"]], unit["occupancy_id"])
        sanity = {
            labels[0]: _curve_sanity(left, unit["method"], particles, margin),
            labels[1]: _curve_sanity(right, unit["method"], particles, margin),
        }
        rows.append(
            {
                **{
                    key: unit[key]
                    for key in ["case_id", "occupancy_id", "substeps", "method"]
                },
                "labels": labels,
                "maximum_difference": difference,
                "equality_pass": difference <= tolerance,
                "sanity": sanity,
                "sanity_pass": all(value["passed"] for value in sanity.values()),
            }
        )
    payload = {
        "schema_version": stage["schema_version"],
        "derivation": "stage5c2gR32_deterministic_quadrature_reference_v1",
        "rows": rows,
        "node_registry_pass": node_pass,
        "maximum_difference": max(row["maximum_difference"] for row in rows),
        "equality_passed": all(row["equality_pass"] for row in rows),
        "absolute_sanity_passed": all(row["sanity_pass"] for row in rows),
    }
    payload["passed"] = (
        payload["node_registry_pass"]
        and payload["equality_passed"]
        and payload["absolute_sanity_passed"]
    )
    payload["decision_sha256"] = sha256_payload(payload)
    return payload


def assert_quadrature_semantic_agreement(primary: dict, reference: dict) -> None:
    excluded = {"derivation", "decision_sha256"}
    if {key: value for key, value in primary.items() if key not in excluded} != {
        key: value for key, value in reference.items() if key not in excluded
    }:
        raise RuntimeError("R3.2 primary/reference quadrature semantics disagree")
