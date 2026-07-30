from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT / "scripts"))
from haxs.validation.hierarchical_validity import evaluate_metric_groups, joint_nested_bootstrap, nested_bootstrap_interval
from stage5c2gR2_common import build_candidate, discover_runtime_files, environment_spec, plan_g1, plan_g2, plan_g3, plan_g4, production_label_parameters, sha256_file, sha256_payload, verify_environment, verify_environment_lock_consistency
from stage5c2gR2_state import atomic_write_json, build_raw_manifest, verify_gate_state, verify_raw_manifest, verify_supervisor_authorization, write_gate_state
from stage5c2gR2_merge import deterministic_merge_csv


def candidate_lock() -> dict:
    payload = build_candidate(ROOT, os.environ.get("HAXS_CUSTODY_ROOT", str(ROOT)))
    return {"candidate_sha256": sha256_payload(payload), "candidate_payload": payload}


def test_canonical_plans_have_frozen_expected_counts() -> None:
    import yaml
    configs = {gate: yaml.safe_load((ROOT / path).read_text()) for gate, path in {"G1": "configs/stage5c2gR2/g1.yaml", "G2": "configs/stage5c2gR2/g2_transport.yaml", "G3": "configs/stage5c2gR2/g3_validity.yaml", "G4": "configs/stage5c2gR2/g4_fixed_count.yaml"}.items()}
    assert len(plan_g1(configs["G1"])) == 128
    assert len(plan_g2(configs["G2"])) == 2 * 2 * 13 * 128
    assert len(plan_g3(configs["G3"])) == 4 * 2 * 4 * 4 * 4
    assert len(plan_g4(configs["G4"])) == 2304


def test_g1_uses_production_mapping_for_both_zero_limits() -> None:
    model = {"hopping_t": 0.55, "mobile_eta": 0.55, "lambda_sd": 0.30}
    assert production_label_parameters("static_only", model) == (0.0, 0.0, 0.0, 0.0)
    assert production_label_parameters("mobile_only", model, {"hopping_t": 0.0, "mobile_eta": 0.0}) == (0.0, 0.0, 0.0, 0.0)
    assert production_label_parameters("spin_density_only", model, {"lambda_sd": 0.0}) == (0.0, 0.0, 0.0, 0.0)


def test_external_config_injection_is_rejected_before_lock_check() -> None:
    result = subprocess.run([sys.executable, "scripts/run_stage5c2gR2_calibration_invariants.py", "--config", "altered.yaml"], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode != 0
    assert "accepts no command-line" in result.stdout + result.stderr or "REJECTED" in result.stdout + result.stderr


def test_failure_atomically_revokes_prior_pass(tmp_path: Path) -> None:
    lock = {"candidate_sha256": "candidate"}; path = tmp_path / "results/stage5c2gR2/state/G1.json"
    write_gate_state("G1", "PASSED", lock, "config", "plan", "attempt1", root=tmp_path)
    write_gate_state("G1", "FAILED", lock, "config", "plan", "attempt2", error="failed", root=tmp_path)
    state = json.loads(path.read_text()); assert state["status"] == "FAILED" and state["attempt_id"] == "attempt2" and state["sequence"] == 2
    with pytest.raises(RuntimeError, match="not a current PASS"): verify_gate_state("G1", lock, tmp_path)


def test_fabricated_all_zero_gate_digest_fails(tmp_path: Path) -> None:
    path = tmp_path / "results/stage5c2gR2/state/G1.json"; path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"gate": "G1", "status": "PASSED", "state_sha256": "0" * 64}), encoding="utf-8")
    with pytest.raises(RuntimeError, match="digest"): verify_gate_state("G1", candidate_lock(), tmp_path)


def test_fabricated_supervisor_receipt_cannot_authorize_unverified_gate(tmp_path: Path) -> None:
    path = tmp_path / "receipt.txt"; path.write_text("0" * 64, encoding="utf-8")
    with pytest.raises((RuntimeError, FileNotFoundError, KeyError)): verify_supervisor_authorization(path, "G1", candidate_lock(), tmp_path)


def test_extra_root_conftest_plugin_yaml_and_shell_change_exact_file_set(tmp_path: Path) -> None:
    (tmp_path / "model.py").write_text("x=1\n"); baseline = {str(path.relative_to(tmp_path)) for path in discover_runtime_files(tmp_path)}
    for name in ["conftest.py", "plugin.py", "extra.yaml", "run.sh"]: (tmp_path / name).write_text("x\n")
    changed = {str(path.relative_to(tmp_path)) for path in discover_runtime_files(tmp_path)}
    assert changed - baseline == {"conftest.py", "plugin.py", "extra.yaml", "run.sh"}


def test_every_locked_runtime_file_mutation_or_deletion_changes_identity() -> None:
    runtime = {str(path.relative_to(ROOT)): sha256_file(path) for path in discover_runtime_files(ROOT)}
    baseline = sha256_payload(runtime)
    for relative in runtime:
        mutated = dict(runtime); mutated[relative] = "0" * 64
        deleted = dict(runtime); del deleted[relative]
        assert sha256_payload(mutated) != baseline
        assert sha256_payload(deleted) != baseline


def test_candidate_binds_every_canonical_config_and_matching_environment_lock() -> None:
    payload = candidate_lock()["candidate_payload"]
    for identity in payload["canonical_configs"].values():
        assert payload["runtime_file_set"][identity["path"]] == identity["sha256"]
    assert verify_environment_lock_consistency(ROOT) == payload["environment"]["locked_packages"]


def raw_fixture(tmp_path: Path) -> tuple[Path, dict]:
    lock = candidate_lock(); config, config_sha, plan_sha = __import__("stage5c2gR2_common").canonical_config("G1", lock, ROOT); ids = [row["comparison_id"] for row in plan_g1(config)]
    attempt = tmp_path / "attempt"; attempt.mkdir(); files = {}
    for role in ["comparisons", "registry", "attempts"]:
        path = attempt / f"{role}.csv"; pd.DataFrame({"comparison_id": ids, "value": np.arange(len(ids))}).to_csv(path, index=False); files[role] = path
    curves = attempt / "curves.csv"; pd.DataFrame({"time": [0.0], "value": [1.0]}).to_csv(curves, index=False); files["curves"] = curves
    manifest = build_raw_manifest("G1", attempt, files, ids, ids, lock, config_sha, plan_sha, "attempt")
    manifest_path = attempt / "MANIFEST.json"; atomic_write_json(manifest_path, manifest); return manifest_path, lock


def test_raw_output_corruption_fails(tmp_path: Path) -> None:
    manifest, lock = raw_fixture(tmp_path); verify_raw_manifest(manifest, lock, "G1", ROOT)
    pd.DataFrame({"comparison_id": ["id"], "value": [999]}).to_csv(manifest.parent / "comparisons.csv", index=False)
    with pytest.raises(RuntimeError, match="changed"): verify_raw_manifest(manifest, lock, "G1", ROOT)


def test_wrong_upstream_config_identity_fails(tmp_path: Path) -> None:
    manifest, lock = raw_fixture(tmp_path); payload = json.loads(manifest.read_text()); payload["canonical_config_sha256"] = "0" * 64; payload["manifest_sha256"] = sha256_payload({k: v for k, v in payload.items() if k != "manifest_sha256"}); atomic_write_json(manifest, payload)
    with pytest.raises(RuntimeError, match="identity"): verify_raw_manifest(manifest, lock, "G1", ROOT)


def test_dependency_environment_mismatch_fails() -> None:
    spec = json.loads(json.dumps(environment_spec())); spec["packages"]["numpy"] = "==0.0.0"
    with pytest.raises(RuntimeError, match="environment"): verify_environment(spec)


@pytest.mark.parametrize("script", ["verify_stage5c2g_protocol_lock.py", "verify_stage5c2gR_protocol_lock.py", "run_stage5c2gR_calibration_invariants.py"])
def test_rejected_legacy_routes_exit_nonzero(script: str) -> None:
    result = subprocess.run([sys.executable, f"scripts/{script}"], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode != 0 and ("REJECTED" in result.stdout + result.stderr or "BLOCKED" in result.stdout + result.stderr)


def hierarchical_frame(seed: int = 1) -> pd.DataFrame:
    generator = np.random.default_rng(seed); rows = []
    occupancy_effect = generator.normal(0, 0.12, 16)
    for occupancy in range(16):
        for path in range(6):
            path_effect = generator.normal(0, 0.05)
            for phase in range(4): rows.append({"occupancy_idx": occupancy, "path_idx": path, "phase_idx": phase, "value": 2.0 + occupancy_effect[occupancy] + path_effect + generator.normal(0, 0.02)})
    return pd.DataFrame(rows)


def test_nested_hierarchical_interval_has_width_and_recovers_known_mean() -> None:
    result = nested_bootstrap_interval(hierarchical_frame(), "value", 1000, 7)
    assert result["ci_low"] < 2.0 < result["ci_high"] and result["standard_error"] > 0


def test_synchronized_joint_bootstrap_preserves_time_covariance() -> None:
    frame = hierarchical_frame(); frame["time_a"] = frame.value; frame["time_b"] = frame.value + 0.25
    result = joint_nested_bootstrap(frame, ["time_a", "time_b"], 1000, 8)
    covariance = np.asarray(result["bootstrap_covariance"])
    assert covariance[0, 1] > 0 and np.isclose(result["means"][1] - result["means"][0], 0.25)


def test_hierarchical_gate_enforces_interval_not_point_estimate() -> None:
    frame = hierarchical_frame().rename(columns={"value": "raw"}); frame["case_id"] = "case"; frame["label"] = "combined"; frame["metric"] = "rmse_db"; frame["value"] = frame.raw; frame["gate_direction"] = "maximum"; frame["gate_threshold"] = 1.99
    result = evaluate_metric_groups(frame, 1000, 9)
    assert result.iloc[0]["mean"] > 1.99 and not bool(result.iloc[0].passed)


def test_synthetic_hierarchical_interval_coverage() -> None:
    covered = 0
    for seed in range(12):
        result = nested_bootstrap_interval(hierarchical_frame(seed), "value", 300, 100 + seed, confidence=0.90)
        covered += int(result["ci_low"] <= 2.0 <= result["ci_high"])
    assert covered >= 9


def test_deterministic_merge_hashes_output_and_rejects_duplicate_ids(tmp_path: Path) -> None:
    left = tmp_path / "b.csv"; right = tmp_path / "a.csv"; pd.DataFrame({"run_id": ["b"], "value": [2]}).to_csv(left, index=False); pd.DataFrame({"run_id": ["a"], "value": [1]}).to_csv(right, index=False)
    first = deterministic_merge_csv([left, right], tmp_path / "merged.csv", ["a", "b"]); second = deterministic_merge_csv([right, left], tmp_path / "merged2.csv", ["a", "b"])
    assert first["sha256"] == second["sha256"]
    pd.DataFrame({"run_id": ["a"], "value": [3]}).to_csv(left, index=False)
    with pytest.raises(RuntimeError, match="duplicate"): deterministic_merge_csv([left, right], tmp_path / "bad.csv", ["a", "b"])
