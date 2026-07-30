from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml
import tomllib

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from calibrate_stage5c2gR32_statistical_sanity import _critical_value, _wilson
from stage5c2gR32_common import quadrature_initial_spins, sha256_payload
from stage5c2gR32_semantics import _curve_sanity


def test_complete_css_x_quadrature_is_unique_weighted_and_deterministic() -> None:
    phase_values = [
        [0.5, -0.5, -0.5],
        [0.5, -0.5, 0.5],
        [0.5, 0.5, -0.5],
        [0.5, 0.5, 0.5],
    ]
    first, registry = quadrature_initial_spins(6, [2], phase_values)
    second, repeated = quadrature_initial_spins(6, [2], phase_values)
    assert first.shape == (1024, 6, 3)
    assert np.array_equal(first, second)
    assert registry == repeated
    assert len({row["phase_code"] for row in registry}) == 1024
    assert [row["node_index"] for row in registry] == list(range(1024))
    assert sum(row["weight"] for row in registry) == pytest.approx(1.0)
    assert np.all(first[:, 2, :] == 0.0)
    assert np.all(first[:, [0, 1, 3, 4, 5], 0] == 0.5)
    assert np.mean(first[:, [0, 1, 3, 4, 5], 1:], axis=0) == pytest.approx(0.0)


def _valid_surrogate_frame() -> pd.DataFrame:
    times = np.linspace(0.0, 1.4, 45)
    sx = 2.5 - 0.1 * times
    sy = 0.01 * np.sin(times)
    sz = 0.01 * np.cos(times) - 0.01
    norm2 = sx * sx + sy * sy + sz * sz
    xi2 = 1.0 + 0.1 * times
    min_var = xi2 * norm2 / 5.0
    return pd.DataFrame(
        {
            "time": times,
            "Sx": sx,
            "Sy": sy,
            "Sz": sz,
            "xi2": xi2,
            "xi2_db": 10.0 * np.log10(xi2),
            "min_var": min_var,
            "spin_length": np.sqrt(norm2) / 2.5,
            "N_eff": 5.0,
            "active_bonds": 3.0,
            "hole_spin_covariance": 0.0,
        }
    )


def test_hard_bound_accepts_valid_quadrature_and_rejects_injected_violation() -> None:
    valid = _valid_surrogate_frame()
    decision = _curve_sanity(valid, "surrogate", 5, 1.0e-10)
    assert decision["passed"]
    forged = valid.copy()
    forged.loc[1, "Sx"] = 2.5001
    forged_decision = _curve_sanity(forged, "surrogate", 5, 1.0e-10)
    assert not forged_decision["passed"]
    assert not forged_decision["checks"]["collective_component_bounds"]


def test_statistical_rule_is_preregistered_and_familywise() -> None:
    config = yaml.safe_load(
        (ROOT / "configs/stage5c2gR32/sanity_calibration.yaml").read_text()
    )["stage5c2gR32_sanity_calibration"]
    assert config["primary_rule"] == "bonferroni_one_sided_normal_envelope"
    assert config["familywise_alpha"] == 0.01
    assert config["binding_sesoi_fraction_of_half_particle_count"] == 0.005
    assert config["pass_criteria"][
        "maximum_benign_familywise_false_rejection"
    ] == 0.01
    assert _critical_value(config["primary_rule"], 0.01, 135) > 3.0


def test_wilson_interval_fail_closes_small_or_high_error_campaigns() -> None:
    low, high = _wilson(0, 1024)
    assert low == 0.0
    assert high < 0.015
    _, high_bad = _wilson(20, 1024)
    assert high_bad > 0.015


def test_protocol_forbids_predecessor_retry_and_all_downstream_scopes() -> None:
    protocol = yaml.safe_load(
        (ROOT / "configs/stage5c2gR32/protocol.yaml").read_text()
    )["stage5c2gR32_protocol"]
    assert protocol["predecessor_disposition"] == "immutable_failed_never_retry"
    assert protocol["predecessor_receipt_reusable"] is False
    assert protocol["authorization"]["same_candidate_retry_forbidden"] is True
    assert protocol["authorization"]["current_receipt_reuse_forbidden"] is True
    assert {"G2", "G3", "G4", "STAGE5C3", "STAGE5D", "PUBLIC_RELEASE"} <= set(
        protocol["blocked_scopes"]
    )


def test_receipt_template_has_exact_fail_closed_scope() -> None:
    template = json.loads(
        (ROOT / "configs/stage5c2gR32/structured_receipt_template.json").read_text()
    )
    assert template["authorized_scope"] == "G1_ONLY"
    assert template["decision"] == "ACCEPT_AND_AUTHORIZE_G1_ONLY"
    assert template["blocked_scopes"] == [
        "G2",
        "G3",
        "G4",
        "STAGE5C3",
        "STAGE5D",
        "MANUSCRIPT_RESULT_CLAIMS",
        "EXACT_MOBILE_HOLE_CLAIMS",
        "PUBLIC_RELEASE",
    ]


def test_candidate_hash_excludes_no_scientific_identity_fields() -> None:
    payload = {
        "runtime_tree_sha256": "a" * 64,
        "wheel_sha256": "b" * 64,
        "S01": "c" * 64,
        "S02": "d" * 64,
        "S03": "e" * 64,
    }
    original = sha256_payload(payload)
    for key in payload:
        changed = dict(payload)
        changed[key] = "f" * 64
        assert sha256_payload(changed) != original


def test_package_and_runtime_versions_are_consistent() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    namespace = {}
    exec((ROOT / "src/haxs/version.py").read_text(), namespace)
    assert project["project"]["version"] == namespace["__version__"] == "0.8.3"
