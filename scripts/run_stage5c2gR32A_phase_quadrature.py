#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from haxs.lattice.graphs import hypercubic_lattice
from haxs.methods.constrained_spin_hole import run_constrained_curve
from haxs.methods.dtwa import collective_samples, run_dtwa
from stage5c2gR3_common import production_label_parameters
from stage5c2gR32_common import atomic_write_json, quadrature_initial_spins, require_new_output, sha256_payload, stable_uuid
from stage5c2gR32_semantics import assert_quadrature_semantic_agreement, derive_quadrature_decision, derive_quadrature_decision_reference
from stage5c2gR32A_common import predecessor_identity, write_manifest


def _frame(result: dict, metadata: dict, schema: str) -> pd.DataFrame:
    frame = pd.DataFrame(result["data"], columns=result["columns"])
    for key, value in reversed(list(metadata.items())):
        frame.insert(0, key, value)
    frame.insert(0, "schema_version", schema)
    return frame


def _convergence(curves: pd.DataFrame, stage: dict) -> pd.DataFrame:
    rows = []
    floor = float(stage["dt_convergence"]["absolute_floor"])
    required = float(stage["dt_convergence"]["minimum_refinement_ratio"])
    columns = list(stage["dt_convergence"]["observable_columns"])
    levels = list(map(int, stage["integration_substeps"]))
    for identity, group in curves.groupby(["case_id", "occupancy_id", "label"], sort=True):
        by = {int(s): f.sort_values("time") for s, f in group.groupby("substeps")}
        if set(by) != set(levels):
            raise RuntimeError(f"missing refinement level: {identity}")
        errors = []
        for left, right in zip(levels[:-1], levels[1:]):
            errors.append(float(np.max(np.abs(by[left][columns].to_numpy(float) - by[right][columns].to_numpy(float)))))
        ratios = [float("inf") if errors[i + 1] <= floor else errors[i] / errors[i + 1] for i in range(len(errors) - 1)]
        passed = all((errors[i] <= floor and errors[i + 1] <= floor) or ratios[i] >= required for i in range(len(ratios)))
        rows.append({
            "case_id": identity[0], "occupancy_id": identity[1], "label": identity[2],
            "errors": json.dumps(errors), "refinement_ratios": json.dumps(ratios),
            "minimum_refinement_ratio": min(ratios), "minimum_required_ratio": required,
            "passed": passed,
        })
    return pd.DataFrame(rows)


def run(config_path: Path, out: Path) -> dict:
    stage = yaml.safe_load(config_path.read_text(encoding="utf-8"))["stage5c2gR32_G1"]
    predecessors = predecessor_identity()
    output = require_new_output(out)
    times = np.linspace(float(stage["times"]["start"]), float(stage["times"]["stop"]), int(stage["times"]["points"]))
    surrogate_frames, exact_frames, node_rows, population_rows, unit_rows = [], [], [], [], []

    for case in stage["cases"]:
        graph = hypercubic_lattice(tuple(case["shape"]), False)
        for occupancy_spec in case["occupancies"]:
            holes = list(map(int, occupancy_spec["holes"]))
            occupied = np.ones(graph.n_sites, dtype=bool)
            occupied[holes] = False
            spins, registry = quadrature_initial_spins(graph.n_sites, holes, stage["quadrature"]["phase_values"])
            unit_id = stable_uuid(stage["namespace_uuid"], case["id"], occupancy_spec["occupancy_id"])
            unit_rows.append({
                "unit_id": unit_id, "case_id": case["id"], "occupancy_id": occupancy_spec["occupancy_id"],
                "particle_count": int(occupied.sum()), "node_count": len(spins),
            })
            for row in registry:
                node_rows.append({
                    "schema_version": stage["schema_version"], "unit_id": unit_id,
                    "node_id": stable_uuid(stage["namespace_uuid"], unit_id, row["node_index"]),
                    "case_id": case["id"], "occupancy_id": occupancy_spec["occupancy_id"], **row,
                })
            for label_index, label in enumerate(case["labels"]):
                hopping, exact_lambda, eta, surrogate_lambda = production_label_parameters(label, stage["model"], case.get("overrides"))
                exact = run_constrained_curve(graph, times, holes, j_perp=float(stage["model"]["j_perp"]), jz=float(stage["model"]["jz"]), hopping_t=hopping, lambda_sd=exact_lambda)
                for substeps in stage["integration_substeps"]:
                    exact_frames.append(_frame(exact, {
                        "case_id": case["id"], "occupancy_id": occupancy_spec["occupancy_id"],
                        "substeps": int(substeps), "method": "exact", "label": label,
                    }, stage["schema_version"]))
                    finest = int(substeps) == int(stage["population_substeps"]) and label_index == 0
                    surrogate = run_dtwa(
                        graph, times, j_perp=float(stage["model"]["j_perp"]), jz=float(stage["model"]["jz"]),
                        mobile_eta=eta, lambda_sd=surrogate_lambda, initial_occupancy=occupied,
                        fixed_hole_count=len(holes), initial_spins=spins, integration_substeps=int(substeps),
                        store_trajectories=finest,
                    )
                    surrogate_frames.append(_frame(surrogate, {
                        "case_id": case["id"], "occupancy_id": occupancy_spec["occupancy_id"],
                        "substeps": int(substeps), "method": "surrogate", "label": label,
                    }, stage["schema_version"]))
                    if finest:
                        snapshots = surrogate["stored_trajectories"]
                        if len(snapshots) != len(times):
                            raise RuntimeError("finest quadrature population snapshots incomplete")
                        for time_index, snapshot in enumerate(snapshots):
                            samples = collective_samples(snapshot, occupied)
                            for node_index, values in enumerate(samples):
                                population_rows.append({
                                    "unit_id": unit_id, "case_id": case["id"],
                                    "occupancy_id": occupancy_spec["occupancy_id"],
                                    "node_index": node_index, "time_index": time_index,
                                    "time": float(times[time_index]), "Sx": float(values[0]),
                                    "Sy": float(values[1]), "Sz": float(values[2]),
                                })

    surrogate = pd.concat(surrogate_frames, ignore_index=True)
    exact = pd.concat(exact_frames, ignore_index=True)
    nodes = pd.DataFrame(node_rows)
    population = pd.DataFrame(population_rows)
    units = pd.DataFrame(unit_rows)
    convergence = _convergence(surrogate, stage)
    paths = {
        "nodes": output / "quadrature_node_registry.csv",
        "surrogate": output / "weighted_surrogate_curves.csv",
        "exact": output / "matched_exact_curves.csv",
        "population": output / "quadrature_collective_population.csv",
        "units": output / "unit_registry.csv",
        "convergence": output / "dt_convergence.csv",
    }
    for name, frame in [("nodes", nodes), ("surrogate", surrogate), ("exact", exact), ("population", population), ("units", units), ("convergence", convergence)]:
        frame.to_csv(paths[name], index=False)
    if len(population) != int(stage["expected_population_rows"]):
        raise RuntimeError("quadrature population row count differs from plan")

    config = {"stage5c2gR32_G1": stage}
    primary = derive_quadrature_decision(paths["surrogate"], paths["exact"], paths["nodes"], config)
    reference = derive_quadrature_decision_reference(paths["surrogate"], paths["exact"], paths["nodes"], config)
    assert_quadrature_semantic_agreement(primary, reference)
    tol = float(stage["analytic_t0_tolerance"])
    t0 = population[population["time_index"] == 0]
    analytic_t0 = bool(
        np.max(np.abs(t0["Sx"].to_numpy(float) - 2.5)) <= tol
        and np.max(np.abs(t0[["Sy", "Sz"]].mean().to_numpy(float))) <= tol
    )
    primary["analytic_t0_passed"] = analytic_t0
    primary["dt_convergence_passed"] = bool(convergence["passed"].all())
    primary["passed"] = bool(primary["passed"] and analytic_t0 and primary["dt_convergence_passed"])
    primary["decision_sha256"] = sha256_payload({k: v for k, v in primary.items() if k != "decision_sha256"})
    atomic_write_json(output / "semantic_decision.json", primary)
    atomic_write_json(output / "semantic_decision_reference.json", reference)
    atomic_write_json(output / "predecessor_identity.json", predecessors)
    manifest = write_manifest(output, "haxs.stage5c2gR32A.deterministic-manifest.v1")
    result = {
        "stage": "R3.2A-S02", "status": "PASS" if primary["passed"] else "FAIL",
        "quadrature_units": len(units), "quadrature_nodes": len(nodes),
        "population_rows": len(population), "maximum_difference": primary["maximum_difference"],
        "absolute_sanity_passed": primary["absolute_sanity_passed"],
        "analytic_t0_passed": analytic_t0, "dt_convergence_passed": primary["dt_convergence_passed"],
        "independent_semantics_agree": True, "decision_sha256": primary["decision_sha256"],
        "manifest_sha256": manifest["manifest_sha256"], "candidate_created": False,
        "next": "R3.2A-S03-DEVELOPMENT" if primary["passed"] else "STOP",
    }
    atomic_write_json(output / "verification.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "configs/stage5c2gR32A/g1_deterministic.yaml")
    parser.add_argument("--out", type=Path, default=ROOT / "output/stage5c2gR32A/g1_preflight")
    args = parser.parse_args()
    result = run(args.config, args.out)
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
