#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
INSTALLED_TARGET = os.environ.get("HAXS_R32_INSTALLED_TARGET")
if INSTALLED_TARGET:
    sys.path.insert(0, str(Path(INSTALLED_TARGET).resolve()))
else:
    sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from haxs.lattice.graphs import hypercubic_lattice
from haxs.methods.constrained_spin_hole import run_constrained_curve
from haxs.methods.dtwa import run_dtwa
from stage5c2gR3_common import production_label_parameters
from stage5c2gR32_common import (
    atomic_write_json,
    file_manifest,
    quadrature_initial_spins,
    require_new_output,
    sha256_payload,
    stable_uuid,
)
from stage5c2gR32_semantics import (
    assert_quadrature_semantic_agreement,
    derive_quadrature_decision,
    derive_quadrature_decision_reference,
)


def _frame(result: dict, metadata: dict, schema: str) -> pd.DataFrame:
    frame = pd.DataFrame(result["data"], columns=result["columns"])
    for key, value in reversed(list(metadata.items())):
        frame.insert(0, key, value)
    frame.insert(0, "schema_version", schema)
    return frame


def _convergence(curves: pd.DataFrame, stage: dict) -> list[dict]:
    rows = []
    floor = float(stage["dt_convergence"]["absolute_floor"])
    minimum_ratio = float(stage["dt_convergence"]["minimum_refinement_ratio"])
    observables = list(stage["dt_convergence"]["observable_columns"])
    keys = ["case_id", "occupancy_id", "label"]
    for identity, group in curves.groupby(keys, sort=True):
        by_substeps = {
            int(value): frame.sort_values("time")
            for value, frame in group.groupby("substeps", sort=True)
        }
        if set(by_substeps) != set(map(int, stage["integration_substeps"])):
            raise RuntimeError(f"missing dt refinement level: {identity}")
        coarse = float(
            np.max(
                np.abs(
                    by_substeps[1][observables].to_numpy(float)
                    - by_substeps[2][observables].to_numpy(float)
                )
            )
        )
        fine = float(
            np.max(
                np.abs(
                    by_substeps[2][observables].to_numpy(float)
                    - by_substeps[4][observables].to_numpy(float)
                )
            )
        )
        ratio = float("inf") if fine <= floor else coarse / fine
        passed = (coarse <= floor and fine <= floor) or ratio >= minimum_ratio
        rows.append(
            {
                **dict(zip(keys, identity)),
                "coarse_to_medium_max_abs": coarse,
                "medium_to_fine_max_abs": fine,
                "refinement_ratio": ratio,
                "minimum_required_ratio": minimum_ratio,
                "passed": passed,
            }
        )
    return rows


def run(config_path: Path, out: Path) -> dict:
    s01 = ROOT / "results/stage5c2gR32/S01/verification.json"
    if not s01.is_file() or json.loads(s01.read_text(encoding="utf-8")).get("status") != "PASS":
        raise RuntimeError("S02 is blocked until S01 immutable reconstruction passes")
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    stage = config["stage5c2gR32_G1"]
    output = require_new_output(out)
    times = np.linspace(
        float(stage["times"]["start"]),
        float(stage["times"]["stop"]),
        int(stage["times"]["points"]),
    )
    surrogate_frames: list[pd.DataFrame] = []
    exact_frames: list[pd.DataFrame] = []
    node_rows: list[dict] = []
    component_rows: list[dict] = []

    for case in stage["cases"]:
        graph = hypercubic_lattice(tuple(case["shape"]), False)
        for occupancy in case["occupancies"]:
            holes = list(map(int, occupancy["holes"]))
            occupied = np.ones(graph.n_sites, dtype=bool)
            occupied[holes] = False
            spins, registry = quadrature_initial_spins(
                graph.n_sites, holes, stage["quadrature"]["phase_values"]
            )
            if len(spins) != int(stage["quadrature"]["expected_nodes_per_unit"]):
                raise RuntimeError("quadrature node count differs from frozen configuration")
            unit_id = stable_uuid(
                stage["namespace_uuid"], case["id"], occupancy["occupancy_id"]
            )
            for row in registry:
                node_rows.append(
                    {
                        "schema_version": stage["schema_version"],
                        "unit_id": unit_id,
                        "node_id": stable_uuid(
                            stage["namespace_uuid"], unit_id, row["node_index"]
                        ),
                        "case_id": case["id"],
                        "occupancy_id": occupancy["occupancy_id"],
                        **row,
                    }
                )
            for label in case["labels"]:
                hopping, exact_lambda, eta, surrogate_lambda = production_label_parameters(
                    label, stage["model"], case.get("overrides")
                )
                exact = run_constrained_curve(
                    graph,
                    times,
                    holes,
                    j_perp=float(stage["model"]["j_perp"]),
                    jz=float(stage["model"]["jz"]),
                    hopping_t=hopping,
                    lambda_sd=exact_lambda,
                )
                for substeps in stage["integration_substeps"]:
                    exact_frames.append(
                        _frame(
                            exact,
                            {
                                "case_id": case["id"],
                                "occupancy_id": occupancy["occupancy_id"],
                                "substeps": int(substeps),
                                "method": "exact",
                                "label": label,
                            },
                            stage["schema_version"],
                        )
                    )
                    surrogate = run_dtwa(
                        graph,
                        times,
                        j_perp=float(stage["model"]["j_perp"]),
                        jz=float(stage["model"]["jz"]),
                        mobile_eta=eta,
                        lambda_sd=surrogate_lambda,
                        initial_occupancy=occupied,
                        fixed_hole_count=len(holes),
                        initial_spins=spins,
                        integration_substeps=int(substeps),
                    )
                    frame = _frame(
                        surrogate,
                        {
                            "case_id": case["id"],
                            "occupancy_id": occupancy["occupancy_id"],
                            "substeps": int(substeps),
                            "method": "surrogate",
                            "label": label,
                        },
                        stage["schema_version"],
                    )
                    surrogate_frames.append(frame)
                    for component in ["Sx", "Sy", "Sz"]:
                        values = frame[component].to_numpy(float)
                        component_rows.append(
                            {
                                "case_id": case["id"],
                                "occupancy_id": occupancy["occupancy_id"],
                                "substeps": int(substeps),
                                "label": label,
                                "component": component,
                                "maximum_absolute_value": float(np.max(np.abs(values))),
                                "particle_half_bound": float(occupied.sum()) / 2.0,
                                "overshoot": float(
                                    max(0.0, np.max(np.abs(values)) - occupied.sum() / 2.0)
                                ),
                            }
                        )

    surrogate_curves = pd.concat(surrogate_frames, ignore_index=True)
    exact_curves = pd.concat(exact_frames, ignore_index=True)
    nodes = pd.DataFrame(node_rows)
    components = pd.DataFrame(component_rows)
    convergence = pd.DataFrame(_convergence(surrogate_curves, stage))
    paths = {
        "nodes": output / "quadrature_node_registry.csv",
        "surrogate": output / "weighted_surrogate_curves.csv",
        "exact": output / "matched_exact_curves.csv",
        "components": output / "component_maxima.csv",
        "convergence": output / "dt_convergence.csv",
    }
    nodes.to_csv(paths["nodes"], index=False)
    surrogate_curves.to_csv(paths["surrogate"], index=False)
    exact_curves.to_csv(paths["exact"], index=False)
    components.to_csv(paths["components"], index=False)
    convergence.to_csv(paths["convergence"], index=False)

    primary = derive_quadrature_decision(
        paths["surrogate"], paths["exact"], paths["nodes"], config
    )
    reference = derive_quadrature_decision_reference(
        paths["surrogate"], paths["exact"], paths["nodes"], config
    )
    assert_quadrature_semantic_agreement(primary, reference)
    primary["dt_convergence_passed"] = bool(convergence["passed"].all())
    primary["passed"] = bool(primary["passed"] and primary["dt_convergence_passed"])
    primary["decision_sha256"] = sha256_payload(
        {key: value for key, value in primary.items() if key != "decision_sha256"}
    )
    atomic_write_json(output / "semantic_decision.json", primary)
    atomic_write_json(output / "semantic_decision_reference.json", reference)
    manifest_records = file_manifest(output)
    manifest = {
        "schema_version": "haxs.stage5c2gR32.S02-manifest.v1",
        "stage": "S02",
        "config_sha256": __import__("hashlib").sha256(
            config_path.read_bytes()
        ).hexdigest(),
        "files": manifest_records,
    }
    manifest["manifest_sha256"] = sha256_payload(manifest)
    atomic_write_json(output / "MANIFEST.json", manifest)
    result = {
        "stage": "S02",
        "status": "PASS" if primary["passed"] else "FAIL",
        "quadrature_units": int(stage["expected_units"]),
        "quadrature_nodes": len(nodes),
        "weighted_curve_rows": len(surrogate_curves),
        "exact_curve_rows": len(exact_curves),
        "maximum_difference": primary["maximum_difference"],
        "absolute_sanity_passed": primary["absolute_sanity_passed"],
        "dt_convergence_passed": primary["dt_convergence_passed"],
        "decision_sha256": primary["decision_sha256"],
        "manifest_sha256": manifest["manifest_sha256"],
        "next": "S03" if primary["passed"] else "STOP_REPAIR_DTWA",
    }
    atomic_write_json(output / "verification.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "configs/stage5c2gR32/g1_phase_quadrature.yaml",
    )
    parser.add_argument(
        "--out", type=Path, default=ROOT / "output/stage5c2gR32/g1_preflight"
    )
    args = parser.parse_args()
    result = run(args.config, args.out)
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
