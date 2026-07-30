from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
CUSTODY_ROOT = Path(os.environ.get("HAXS_CUSTODY_ROOT", str(ROOT))).resolve()
sys.path.insert(0, str(ROOT / "scripts"))
from check_stage5c2f_hierarchy import audit_registry
from analyze_stage5c2f import balanced_nested_bootstrap_ci, normalize_units, paired_effects
from stage5c2f_common import planned_registry


def load_config() -> dict:
    return yaml.safe_load((ROOT / "configs/stage5c2f/primary_lock.yaml").read_text(encoding="utf-8"))


def test_preregistered_design_is_fresh_balanced_and_scoped() -> None:
    st = load_config()["stage5c2f"]
    assert st["preregistered_design"] == "balanced_fresh"
    assert st["preregistration_status"] == "locked_before_new_results"
    assert st["design"] == {"occupancies": 16, "paths_per_occupancy": 6, "phase_batches_per_path": 4}
    assert st["gates"]["absolute_mc_se_at_most"] == 0.05
    assert st["gates"]["equivalence_margin_db"] == 0.25


def test_planned_hierarchy_and_confirmation_namespaces_pass() -> None:
    raw = load_config()
    planned = planned_registry(raw)
    confirmation = pd.read_csv(CUSTODY_ROOT / raw["stage5c2f"]["locked_confirmation"] / "stage5c2d_seed_registry.csv")
    table, summary = audit_registry(planned, raw, confirmation)
    assert summary["status"] == "PASS", table[~table.passed].to_dict("records")
    assert len(planned) == 16 * 6 * 4 * 2


def test_multiple_physical_occupancies_under_one_index_hard_fail() -> None:
    raw = load_config()
    registry = planned_registry(raw)
    registry["occupancy_hash"] = registry["occupancy_realization_id"]
    victim = registry.index[(registry.occupancy_idx == 0) & (registry.path_idx == 5)][0]
    registry.loc[victim, "occupancy_hash"] = "different-physical-occupancy"
    table, summary = audit_registry(registry, raw)
    assert summary["status"] == "FAIL"
    assert "one_occupancy_hash_per_level" in summary["failed_checks"]
    assert not table.loc[table.check == "one_occupancy_hash_per_level", "passed"].iloc[0]


def test_cross_block_seed_collision_hard_fail() -> None:
    raw = load_config()
    registry = planned_registry(raw)
    confirmation = pd.read_csv(CUSTODY_ROOT / raw["stage5c2f"]["locked_confirmation"] / "stage5c2d_seed_registry.csv")
    confirmation.loc[confirmation.index[0], "occupancy_seed"] = int(registry.occupancy_seed.iloc[0])
    _, summary = audit_registry(registry, raw, confirmation)
    assert "primary_confirmation_seed_disjoint" in summary["failed_checks"]


def test_every_generated_row_contract_is_present_in_runner_source() -> None:
    source = (ROOT / "scripts/run_stage5c2f_primary_lock.py").read_text(encoding="utf-8")
    for field in ["parent_config_hash", "generating_config_hash", "occupancy_realization_id", "path_realization_id", "phase_realization_id", "attempt_ledger"]:
        assert field in source


def test_source_generated_decision_matches_golden_failure(tmp_path: Path) -> None:
    analysis = tmp_path / "analysis"
    analysis.mkdir()
    row = {
        "block": "primary", "fixed_time_mean_pass": True, "fixed_time_ci_pass": True,
        "absolute_mc_se_pass": False, "occupancy_negative_fraction_pass": True,
        "local_window_all_negative": True, "equivalence_pass": True,
    }
    pd.DataFrame([row, {**row, "block": "confirmation", "absolute_mc_se_pass": True}]).to_csv(analysis / "stage5c2f_gate_table.csv", index=False)
    hierarchy = tmp_path / "hierarchy.json"
    hierarchy.write_text(json.dumps({"status": "PASS"}), encoding="utf-8")
    completed = subprocess.run([sys.executable, "scripts/make_stage5c2f_decision.py", "--analysis", str(analysis), "--hierarchy-gate", str(hierarchy)], cwd=ROOT, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    actual = json.loads((analysis / "stage5c2f_decision.json").read_text(encoding="utf-8"))
    expected = json.loads((ROOT / "tests/stage5c2f/golden_decision_failure.json").read_text(encoding="utf-8"))
    assert actual == expected


def test_canonical_locked_confirmation_is_complete() -> None:
    path = CUSTODY_ROOT / load_config()["stage5c2f"]["locked_confirmation"]
    assert {item.name for item in path.iterdir()} >= {"stage5c2d_finals.csv", "stage5c2d_curves_all.csv", "stage5c2d_seed_registry.csv", "stage5c2d_block_manifest.json"}


def test_frozen_confirmation_pairs_by_physical_occupancy_and_nested_indices() -> None:
    path = CUSTODY_ROOT / load_config()["stage5c2f"]["locked_confirmation"]
    finals = normalize_units(pd.read_csv(path / "stage5c2d_finals.csv"), confirmation=True)
    effects = paired_effects(finals)
    assert len(effects) == 12 * 4 * 4
    assert effects.occupancy_hash.nunique() == 12


def test_vectorized_nested_bootstrap_is_deterministic() -> None:
    rows = []
    for occupancy in range(3):
        for path in range(2):
            for phase in range(2):
                rows.append({"occupancy_idx": occupancy, "path_idx": path, "phase_idx": phase, "effect_db": float(occupancy + path + phase)})
    frame = pd.DataFrame(rows)
    first = balanced_nested_bootstrap_ci(frame, n_boot=200, seed=123)
    second = balanced_nested_bootstrap_ci(frame, n_boot=200, seed=123)
    assert first == second
    assert first[0] < first[1]


def test_legacy_command_contract_is_explicitly_preserved() -> None:
    assert (ROOT / "STAGE3_COMMANDS.sh").is_file()
    assert (ROOT / "STAGE3A_COMMANDS.sh").is_file()
