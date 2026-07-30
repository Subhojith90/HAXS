from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from stage5c2gR32A_common import (
    analytic_normal_power,
    critical_value,
    sample_counts,
    sampled_statistics,
    seed,
    verify_population,
    verify_unit_registry,
    wilson,
)


def _units() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"unit_id": "u1", "case_id": "limit_hopping_zero_chain6", "occupancy_id": "chain6_hole_2", "particle_count": 5, "node_count": 1024},
            {"unit_id": "u2", "case_id": "limit_hopping_zero_chain6", "occupancy_id": "chain6_hole_4", "particle_count": 5, "node_count": 1024},
            {"unit_id": "u3", "case_id": "limit_spin_density_zero_rect2x3", "occupancy_id": "rect2x3_hole_2", "particle_count": 5, "node_count": 1024},
            {"unit_id": "u4", "case_id": "limit_spin_density_zero_rect2x3", "occupancy_id": "rect2x3_hole_3", "particle_count": 5, "node_count": 1024},
        ]
    )


def test_analytic_normal_power_matches_closed_form_fixture() -> None:
    effect, standard_error, critical = 0.02, 0.005, 2.0
    expected = statistics.NormalDist().cdf(effect / standard_error - critical)
    assert analytic_normal_power(effect, standard_error, critical) == pytest.approx(expected, abs=1e-12)


def test_simulated_alternative_is_random_and_matches_analytic_power() -> None:
    rng = np.random.default_rng(9182)
    trials = 200_000
    effect, standard_error, critical = 0.02, 0.01, 1.5
    stochastic_statistics = effect + rng.normal(0.0, standard_error, size=trials)
    empirical = float(np.mean(stochastic_statistics > critical * standard_error))
    expected = analytic_normal_power(effect, standard_error, critical)
    assert np.std(stochastic_statistics) > 0.0
    assert empirical == pytest.approx(expected, abs=0.004)


def test_power_zero_and_one_hundred_percent_edges() -> None:
    assert analytic_normal_power(-1.0, 0.0, 5.0) == 0.0
    assert analytic_normal_power(1.0, 0.0, 5.0) == 1.0
    assert wilson(0, 512)[1] < 0.015
    assert wilson(512, 512)[0] > 0.99


def test_all_four_unit_registry_and_missing_or_duplicate_fail_closed() -> None:
    assert len(verify_unit_registry(_units())) == 4
    with pytest.raises(RuntimeError, match="four unique"):
        verify_unit_registry(_units().iloc[:3])
    duplicate = pd.concat([_units().iloc[:3], _units().iloc[[0]]], ignore_index=True)
    with pytest.raises(RuntimeError, match="four unique"):
        verify_unit_registry(duplicate)


def test_global_family_is_stricter_than_each_case_family() -> None:
    alpha = 0.01
    assert critical_value(alpha, 4 * 45 * 3) > critical_value(alpha, 2 * 45 * 3)


def test_development_and_validation_seed_namespaces_do_not_collide() -> None:
    development = {
        seed("ceba1118-b3c6-43ef-b713-c5f89407d73c", "DEVELOPMENT", i, f"u{j}", "iid")
        for i in range(128)
        for j in range(4)
    }
    validation = {
        seed("6b08ce92-3300-45b0-887c-e1359466acb7", "VALIDATION", i, f"u{j}", "iid")
        for i in range(512)
        for j in range(4)
    }
    assert development.isdisjoint(validation)


def test_frozen_validation_rule_exactly_matches_development_rule() -> None:
    development = yaml.safe_load((ROOT / "configs/stage5c2gR32A/s03_development.yaml").read_text())["stage5c2gR32A_stochastic"]
    validation = yaml.safe_load((ROOT / "configs/stage5c2gR32A/s03_validation.yaml").read_text())["stage5c2gR32A_stochastic"]
    assert development["primary_rule_frozen_for_validation"] == validation["frozen_rule"]
    assert validation["extension"] == {"permitted": False, "final_maximum_reached": True}


def test_iid_sampling_retains_random_alternative_variability() -> None:
    values = np.linspace(-0.5, 0.5, 1024)[:, None]
    means = []
    for index in range(100):
        counts = sample_counts("iid", 1024, 1024, np.random.default_rng(index))
        mean, standard_error = sampled_statistics(values, counts)
        means.append(mean[0])
        assert standard_error[0] > 0.0
    assert np.std(means) > 0.005


def test_population_missing_duplicate_or_invalid_cells_fail_closed() -> None:
    units = verify_unit_registry(_units())
    rows = []
    for unit in units:
        for node in range(1024):
            for time_index in range(45):
                rows.append(
                    {
                        "unit_id": unit["unit_id"], "case_id": unit["case_id"],
                        "occupancy_id": unit["occupancy_id"], "node_index": node,
                        "time_index": time_index, "time": time_index / 10,
                        "Sx": 2.5, "Sy": 0.0, "Sz": 0.0,
                    }
                )
    valid = pd.DataFrame(rows)
    verify_population(valid, units)
    with pytest.raises(RuntimeError, match="incomplete"):
        verify_population(valid.iloc[:-1], units)
    duplicate = pd.concat([valid, valid.iloc[[0]]], ignore_index=True)
    with pytest.raises(RuntimeError, match="duplicate"):
        verify_population(duplicate, units)
    invalid = valid.copy()
    invalid.loc[0, "Sx"] = np.nan
    with pytest.raises(RuntimeError, match="invalid numeric"):
        verify_population(invalid, units)


def test_r32_failure_is_declared_immutable_and_not_a_rule_source() -> None:
    development = yaml.safe_load((ROOT / "configs/stage5c2gR32A/s03_development.yaml").read_text())["stage5c2gR32A_stochastic"]
    assert "stage5c2gR32/sanity_calibration" not in development["deterministic_truth"]
    old = json.loads((ROOT / "output/stage5c2gR32/sanity_calibration/calibration_decision.json").read_text())
    assert old["status"] == "FAIL"
