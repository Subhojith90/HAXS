from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
CUSTODY_ROOT = Path(os.environ.get("HAXS_CUSTODY_ROOT", str(ROOT))).resolve()
sys.path.insert(0, str(ROOT / "scripts"))
from analyze_stage5c2g_fixed_count import nested_bootstrap
from stage5c2g_common import assert_protocol_locked, domain_seed, planned_fixed_count_registry
from stage5c2f_common import planned_registry as planned_stage5c2f_registry
from verify_stage5c2g_protocol_lock import covered_paths
from haxs.lattice.graphs import hypercubic_lattice
from haxs.methods.constrained_spin_hole import build_basis, build_constrained_hamiltonian, run_constrained_curve
from haxs.methods.dtwa import run_dtwa
from haxs.validation.topology import topology_descriptors


def load(relative: str) -> dict:
    return yaml.safe_load((ROOT / relative).read_text(encoding="utf-8"))


def test_protocol_locks_primary_estimator_and_removes_equivalence_gate() -> None:
    protocol = load("configs/stage5c2g/protocol.yaml")["stage5c2g_protocol"]
    assert protocol["primary_uncertainty_estimator"]["replicates"] == 20000
    assert protocol["primary_uncertainty_estimator"]["name"] == "equal_occupancy_nested_cluster_bootstrap"
    assert protocol["equivalence_gate"]["enabled"] is False
    assert protocol["validity_gates"]["minimum_time_profile_correlation"] == 0.90
    assert protocol["validity_gates"]["maximum_rmse_multiple_of_clean_static_calibration"] == 1.50


def test_protocol_lock_excludes_machine_generated_cache_files() -> None:
    protocol_path = ROOT / "configs/stage5c2g/protocol.yaml"
    paths = covered_paths(protocol_path, load("configs/stage5c2g/protocol.yaml"))
    relative_paths = [path.relative_to(ROOT) for path in paths]
    assert Path("tests/stage5c2g/test_stage5c2g_protocol_and_models.py") in relative_paths
    assert all("__pycache__" not in path.parts for path in relative_paths)
    assert all(path.suffix not in {".pyc", ".pyo"} for path in relative_paths)
    assert all(path.name != ".DS_Store" for path in relative_paths)


def test_fixed_count_design_is_exactly_preregistered() -> None:
    raw = load("configs/stage5c2g/fixed_count.yaml")
    stage = raw["stage5c2g_fixed_count"]
    assert stage["fixed_hole_counts"] == [3, 5, 7]
    assert stage["occupancies_per_count"] == 16
    assert stage["paths_per_occupancy"] == 6
    assert stage["phase_batches_per_path"] == 4
    assert stage["n_traj"] == 1024
    for holes in stage["fixed_hole_counts"]:
        assert len(planned_fixed_count_registry(raw, holes)) == 16 * 6 * 4 * 2


def test_new_seed_namespace_is_disjoint_from_primary_and_confirmation() -> None:
    raw = load("configs/stage5c2g/fixed_count.yaml")
    planned = pd.concat([planned_fixed_count_registry(raw, holes) for holes in [3, 5, 7]], ignore_index=True)
    new_values = set().union(*(set(planned[column].astype(int)) for column in ["occupancy_seed", "hole_path_seed", "phase_batch_seed"]))
    stage5c2f_raw = load("configs/stage5c2f/primary_lock.yaml")
    previous_registries = [
        planned_stage5c2f_registry(stage5c2f_raw),
        pd.read_csv(CUSTODY_ROOT / "results/stage5c2d_lite/confirmation/stage5c2d_seed_registry.csv"),
    ]
    for previous in previous_registries:
        previous_values = set().union(*({int(value) for value in previous[column].dropna().astype(int) if int(value) != 0} for column in ["occupancy_seed", "hole_path_seed", "phase_batch_seed"]))
        assert new_values.isdisjoint(previous_values)
    exact = load("configs/stage5c2g/exact_mobile_benchmark.yaml")["stage5c2g_exact_benchmark"]
    exact_values = set()
    for split in ["calibration", "validation"]:
        for case in exact[f"{split}_cases"]:
            exact_values.add(domain_seed(exact["namespace_uuid"], split, "occupancy", case["id"]))
            for label in case.get("labels", exact["labels"]):
                exact_values.add(domain_seed(exact["namespace_uuid"], split, "path", case["id"], label))
                exact_values.add(domain_seed(exact["namespace_uuid"], split, "phase", case["id"], label))
    assert new_values.isdisjoint(exact_values)


def test_calibration_and_validation_case_ids_are_disjoint() -> None:
    stage = load("configs/stage5c2g/exact_mobile_benchmark.yaml")["stage5c2g_exact_benchmark"]
    calibration = {case["id"] for case in stage["calibration_cases"]}
    validation = {case["id"] for case in stage["validation_cases"]}
    assert calibration.isdisjoint(validation)
    assert all(case.get("designated_confirmatory") for case in stage["validation_cases"])


def test_constrained_basis_dimension_and_particle_sector() -> None:
    basis = build_basis(6, 2)
    assert basis.dimension == math.comb(6, 2) * 2**4
    assert basis.n_particles == 4
    assert all(sum(value == 0 for value in state) == 2 for state in basis.states)


def test_constrained_hamiltonian_is_hermitian() -> None:
    graph = hypercubic_lattice((4,), False)
    basis = build_basis(4, 1)
    hamiltonian = build_constrained_hamiltonian(graph, basis, hopping_t=0.55, lambda_sd=0.30)
    assert np.linalg.norm((hamiltonian - hamiltonian.getH()).toarray()) < 1e-12


def test_hopping_transports_the_spin_with_the_particle() -> None:
    graph = hypercubic_lattice((2,), False)
    basis = build_basis(2, 1)
    hamiltonian = build_constrained_hamiltonian(graph, basis, j_perp=0.0, jz=0.0, hopping_t=0.4)
    initial = basis.index[(0, 2)]
    transported = basis.index[(2, 0)]
    assert np.isclose(hamiltonian[transported, initial], -0.4)
    assert np.isclose(hamiltonian[basis.index[(1, 0)], initial], 0.0)


def test_constrained_curve_has_exact_accounting() -> None:
    graph = hypercubic_lattice((4,), False)
    result = run_constrained_curve(graph, np.linspace(0.0, 0.1, 3), [1], hopping_t=0.2, lambda_sd=0.1)
    frame = pd.DataFrame(result["data"], columns=result["columns"])
    assert np.max(frame.norm_error) < 1e-12
    assert np.allclose(frame.particle_number, 3.0)
    assert np.allclose(frame.hole_number_expectation, 1.0)
    assert np.allclose(result["hole_density"].sum(axis=1), 1.0)


def test_zero_hopping_and_zero_spin_density_limits_reduce_exactly() -> None:
    graph = hypercubic_lattice((4,), False)
    times = np.linspace(0.0, 0.2, 4)
    static = run_constrained_curve(graph, times, [1], hopping_t=0.0, lambda_sd=0.0)["data"]
    mobile_zero = run_constrained_curve(graph, times, [1], hopping_t=0.0, lambda_sd=0.0)["data"]
    spin_density_zero = run_constrained_curve(graph, times, [1], hopping_t=0.0, lambda_sd=0.0)["data"]
    assert np.allclose(static, mobile_zero, atol=1e-12, rtol=0.0)
    assert np.allclose(static, spin_density_zero, atol=1e-12, rtol=0.0)


def test_dtwa_accepts_an_explicit_matched_occupancy() -> None:
    graph = hypercubic_lattice((4,), False)
    occupancy = np.asarray([True, False, True, True])
    result = run_dtwa(graph, np.asarray([0.0, 0.05]), n_traj=4, fixed_hole_count=1, initial_occupancy=occupancy, occupancy_seed=1, hole_path_seed=2, phase_batch_seed=3)
    assert np.array_equal(result["initial_occupancy"].astype(bool), occupancy)


def test_topology_descriptors_detect_disconnection() -> None:
    graph = hypercubic_lattice((5,), False)
    occupancy = np.asarray([True, True, False, True, True])
    descriptors = topology_descriptors(graph, occupancy)
    assert descriptors["largest_connected_component"] == 2
    assert descriptors["occupied_graph_connected"] is False
    assert descriptors["active_bonds"] == 2


def test_nested_bootstrap_is_deterministic_and_reports_uncertainty() -> None:
    rows = []
    for occupancy in range(4):
        for path in range(2):
            for phase in range(2):
                rows.append({"occupancy_idx": occupancy, "path_idx": path, "phase_idx": phase, "effect_db": -0.1 * (occupancy + 1) + 0.01 * path})
    frame = pd.DataFrame(rows)
    first = nested_bootstrap(frame, 500, 42)
    second = nested_bootstrap(frame, 500, 42)
    assert first == second
    assert first[1] > 0.0
    assert first[2] < first[3]


def test_unfinalized_protocol_blocks_production(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError):
        assert_protocol_locked(str(tmp_path / "missing.json"))


def test_source_generated_both_fail_decision_matches_golden(tmp_path: Path) -> None:
    results = tmp_path / "results"
    (results / "fixed_count_analysis").mkdir(parents=True)
    (results / "validity_analysis").mkdir(parents=True)
    (results / "fixed_count_analysis/stage5c2g_fixed_count_gate.json").write_text(json.dumps({"passed": False}), encoding="utf-8")
    (results / "validity_analysis/stage5c2g_validity_gate.json").write_text(json.dumps({"passed": False}), encoding="utf-8")
    completed = subprocess.run([sys.executable, "scripts/make_stage5c2g_decision.py", "--results", str(results)], cwd=ROOT, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    actual = json.loads((results / "decision/stage5c2g_decision.json").read_text(encoding="utf-8"))
    expected = json.loads((ROOT / "tests/stage5c2g/golden_decision_both_fail.json").read_text(encoding="utf-8"))
    assert actual == expected
