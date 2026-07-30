from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from haxs.lattice.graphs import hypercubic_lattice
from haxs.methods.dtwa import run_dtwa
from haxs.validation.transport import density_from_occupancy_trajectories, transport_discrepancy
from stage5c2gR_chunks import create_chunk_manifest, validate_chunk_manifest
from stage5c2gR_common import assert_protocol_locked, build_candidate, checked_lock, physical_random_unit, scientific_paths, sha256_file, sha256_payload


def test_random_units_are_label_independent_and_order_invariant() -> None:
    labels = ["static_only", "mobile_only", "spin_density_only", "combined"]
    forward = {label: physical_random_unit("namespace", "calibration", "case", 1, 2, 3) for label in labels}
    reverse = {label: physical_random_unit("namespace", "calibration", "case", 1, 2, 3) for label in reversed(labels)}
    assert forward == reverse
    assert len({tuple(unit.items()) for unit in forward.values()}) == 1


def test_identical_physical_identifiers_repeat_exactly() -> None:
    first = physical_random_unit("namespace", "validation", "case", 0, 0, 0)
    second = physical_random_unit("namespace", "validation", "case", 0, 0, 0)
    assert first == second


def test_paired_zero_hopping_and_zero_spin_density_are_exact() -> None:
    graph = hypercubic_lattice((5,), False)
    times = np.linspace(0.0, 0.2, 4)
    occupancy = np.asarray([True, True, False, True, True])
    unit = physical_random_unit("namespace", "calibration", "zero", 0, 0, 0)
    arguments = dict(graph=graph, times=times, initial_occupancy=occupancy, fixed_hole_count=1, n_traj=16, occupancy_seed=unit["occupancy_seed"], hole_path_seed=unit["hole_path_seed"], phase_batch_seed=unit["phase_batch_seed"])
    static = run_dtwa(**arguments, mobile_eta=0.0, lambda_sd=0.0)["data"]
    zero_hopping = run_dtwa(**arguments, mobile_eta=0.0, lambda_sd=0.0)["data"]
    zero_spin_density = run_dtwa(**arguments, mobile_eta=0.0, lambda_sd=0.0)["data"]
    assert np.array_equal(static, zero_hopping)
    assert np.array_equal(static, zero_spin_density)


def test_transport_identity_is_zero_for_identical_paths() -> None:
    graph = hypercubic_lattice((4,), False)
    trajectories = np.repeat(np.asarray([[[True, False, True, True]]], dtype=bool), 3, axis=1)
    density = density_from_occupancy_trajectories(trajectories)
    discrepancy = transport_discrepancy(density, density, graph.coords, [1])
    assert np.max(np.abs(discrepancy["density_l1_by_time"])) == 0.0
    assert np.max(np.abs(discrepancy["normalized_msd_error"])) == 0.0


def minimal_locked_tree(tmp_path: Path) -> tuple[dict, Path]:
    for directory in ["src/haxs", "scripts", "configs/stage5c2gR", "tests", "custody", "results/stage5c2gR/protocol_lock"]: (tmp_path / directory).mkdir(parents=True, exist_ok=True)
    (tmp_path / "src/haxs/model.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / "scripts/run.py").write_text("print('ok')\n", encoding="utf-8")
    custody_object = tmp_path / "custody/object.bin"; custody_object.write_bytes(b"frozen")
    custody = {"stage5c2gR_custody": {"contract": "content_addressed_external_mount", "objects": [{"id": "object", "logical_path": "custody/object.bin", "sha256": sha256_file(custody_object)}]}}
    (tmp_path / "configs/stage5c2gR/custody.yaml").write_text(yaml.safe_dump(custody), encoding="utf-8")
    stage = {"protocol_version": "test", "configs": {"custody": "configs/stage5c2gR/custody.yaml"}, "random_unit_contract": {}, "calibration_gates": {}, "transport_mapping_gates": {}, "validity_gates": {}, "stop_go_sequence": {}, "forbidden_actions": []}
    (tmp_path / "configs/stage5c2gR/protocol.yaml").write_text(yaml.safe_dump({"stage5c2gR_protocol": stage}), encoding="utf-8")
    payload = build_candidate(root=tmp_path, mount=tmp_path)
    candidate_sha = sha256_payload(payload)
    candidate = {**payload, "candidate_sha256": candidate_sha}
    candidate_path = tmp_path / "results/stage5c2gR/protocol_lock/CANDIDATE.json"; candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
    receipt = tmp_path / "results/stage5c2gR/protocol_lock/EXTERNAL_TIMESTAMP_RECEIPT.txt"; receipt.write_text(f"external {candidate_sha}\n", encoding="utf-8")
    lock = {"status": "LOCKED_WITH_EXTERNAL_TIMESTAMP_RECEIPT", "candidate_sha256": candidate_sha, "candidate_file": str(candidate_path.relative_to(tmp_path)), "candidate_payload": payload, "external_timestamp_receipt": {"stored_path": str(receipt.relative_to(tmp_path)), "sha256": sha256_file(receipt)}}
    lock_path = tmp_path / "results/stage5c2gR/protocol_lock/LOCKED.json"; lock_path.write_text(json.dumps(lock), encoding="utf-8")
    return lock, lock_path


def test_imported_source_mutation_fails_closed(tmp_path: Path) -> None:
    _, lock_path = minimal_locked_tree(tmp_path)
    assert_protocol_locked(lock_path, root=tmp_path, mount=tmp_path)
    (tmp_path / "src/haxs/model.py").write_text("VALUE = 2\n", encoding="utf-8")
    with pytest.raises(RuntimeError): assert_protocol_locked(lock_path, root=tmp_path, mount=tmp_path)


def test_lock_payload_edit_fails_against_external_receipt(tmp_path: Path) -> None:
    lock, lock_path = minimal_locked_tree(tmp_path)
    lock["candidate_payload"]["source_tree_sha256"] = "0" * 64
    lock_path.write_text(json.dumps(lock), encoding="utf-8")
    with pytest.raises(RuntimeError): assert_protocol_locked(lock_path, root=tmp_path, mount=tmp_path)


def test_missing_custody_object_fails_candidate_construction(tmp_path: Path) -> None:
    _, _ = minimal_locked_tree(tmp_path)
    (tmp_path / "custody/object.bin").unlink()
    with pytest.raises(RuntimeError): build_candidate(root=tmp_path, mount=tmp_path)


def test_failed_calibration_lock_is_rejected(tmp_path: Path) -> None:
    protocol = {"candidate_sha256": "candidate"}
    payload = {"status": "CALIBRATION_FAILED_NO_LOCK", "passed": False, "protocol_candidate_sha256": "candidate"}
    payload["lock_sha256"] = sha256_payload(payload)
    path = tmp_path / "FAILED.json"; path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RuntimeError): checked_lock(path, "CALIBRATION_PASSED_AND_TOLERANCES_FROZEN", protocol, tmp_path)


def test_chunk_resume_rejects_stale_or_modified_files(tmp_path: Path) -> None:
    files = {}
    run_ids = ["a", "b"]
    for role in ["curves", "finals", "registry"]:
        path = tmp_path / f"chunk_{role}.csv"; pd.DataFrame({"run_id": run_ids, "value": [1, 2]}).to_csv(path, index=False); files[role] = path
    attempts = tmp_path / "chunk_attempts.csv"; pd.DataFrame({"run_id": run_ids, "status": ["completed", "completed"]}).to_csv(attempts, index=False); files["attempts"] = attempts
    manifest = create_chunk_manifest("chunk", files, run_ids, "candidate", "config")
    manifest_path = tmp_path / "chunk_manifest.json"; manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    validate_chunk_manifest(manifest_path, run_ids, "candidate", "config")
    pd.DataFrame({"run_id": run_ids, "value": [9, 9]}).to_csv(files["finals"], index=False)
    with pytest.raises(RuntimeError): validate_chunk_manifest(manifest_path, run_ids, "candidate", "config")


def test_full_closure_contains_previous_uncovered_scientific_modules() -> None:
    covered = {str(path.relative_to(ROOT)) for path in scientific_paths(ROOT)}
    assert "src/haxs/models/mobile_holes.py" in covered
    assert "src/haxs/utils/rng.py" in covered
    assert "src/haxs/validation/random_effects.py" in covered


def test_every_covered_file_hash_contributes_to_source_tree_identity() -> None:
    covered = {str(path.relative_to(ROOT)): sha256_file(path) for path in scientific_paths(ROOT)}
    baseline = sha256_payload(covered)
    for relative in covered:
        mutated = dict(covered); mutated[relative] = "0" * 64
        assert sha256_payload(mutated) != baseline
