#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2gR_common import assert_protocol_locked, checked_lock, load_yaml, sha256_file, sha256_payload

UNIT = ["case_id", "occupancy_idx", "path_idx", "phase_idx", "block_id", "occupancy_realization_id", "hole_path_realization_id", "phase_batch_realization_id", "exact_initial_state_id"]


def curve_metrics(exact: pd.DataFrame, surrogate: pd.DataFrame) -> tuple[float, float]:
    merged = exact[["time", "xi2_db"]].merge(surrogate[["time", "xi2_db"]], on="time", suffixes=("_exact", "_surrogate"), validate="one_to_one")
    return float(np.corrcoef(merged.xi2_db_exact, merged.xi2_db_surrogate)[0, 1]), float(np.sqrt(np.mean((merged.xi2_db_exact - merged.xi2_db_surrogate) ** 2)))


def main() -> None:
    raise SystemExit("BLOCKED LEGACY ROUTE: Stage 5C.2G-R tolerance locking is not authorized")
    parser = argparse.ArgumentParser()
    parser.add_argument("--calibration", default="results/stage5c2gR/calibration")
    parser.add_argument("--protocol", default="configs/stage5c2gR/protocol.yaml")
    parser.add_argument("--out", default="results/stage5c2gR/validity_tolerances")
    args = parser.parse_args()
    protocol_lock = assert_protocol_locked(protocol_path=args.protocol)
    invariant_lock = checked_lock("results/stage5c2gR/calibration_invariants/LOCKED.json", "PAIRED_CALIBRATION_INVARIANTS_PASSED", protocol_lock)
    mapping = checked_lock("results/stage5c2gR/mobility_mapping/LOCKED.json", "PASSED_AND_FROZEN", protocol_lock)
    protocol = load_yaml(args.protocol)["stage5c2gR_protocol"]
    gates = protocol["calibration_gates"]
    root = ROOT / args.calibration
    manifest_path = root / "stage5c2gR_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not manifest.get("all_attempts_completed") or manifest.get("protocol_candidate_sha256") != protocol_lock["candidate_sha256"] or manifest.get("mapping_lock_sha256") != mapping["lock_sha256"]:
        raise RuntimeError("calibration manifest is incomplete or belongs to different locked inputs")
    exact = pd.read_csv(root / "stage5c2gR_exact_curves.csv")
    surrogate = pd.read_csv(root / "stage5c2gR_surrogate_curves.csv")

    per_unit = []
    for keys, exact_unit in exact.groupby(UNIT + ["label"], sort=True):
        selector = np.ones(len(surrogate), dtype=bool)
        for column, value in zip(UNIT + ["label"], keys): selector &= surrogate[column].astype(str).to_numpy() == str(value)
        surrogate_unit = surrogate.loc[selector]
        correlation, rmse = curve_metrics(exact_unit, surrogate_unit)
        per_unit.append({**dict(zip(UNIT + ["label"], keys)), "correlation": correlation, "rmse_db": rmse})
    per_unit_frame = pd.DataFrame(per_unit)

    clean_cases = ["cal_chain6_one_hole", "cal_rect2x3_one_hole"]
    clean_rows = []
    for case_id in clean_cases:
        for occupancy_idx in sorted(exact.loc[exact.case_id == case_id, "occupancy_idx"].unique()):
            exact_curve = exact[(exact.case_id == case_id) & (exact.occupancy_idx == occupancy_idx) & (exact.label == "static_only")].groupby("time", as_index=False).xi2_db.mean()
            surrogate_curve = surrogate[(surrogate.case_id == case_id) & (surrogate.occupancy_idx == occupancy_idx) & (surrogate.label == "static_only")].groupby("time", as_index=False).xi2_db.mean()
            correlation, rmse = curve_metrics(exact_curve, surrogate_curve)
            clean_rows.append({"case_id": case_id, "occupancy_idx": int(occupancy_idx), "correlation": correlation, "rmse_db": rmse, "correlation_pass": bool(correlation >= float(gates["minimum_clean_static_time_profile_correlation"])), "rmse_pass": bool(rmse <= float(gates["maximum_clean_static_rmse_db"]))})
    clean = pd.DataFrame(clean_rows)

    limit_rows = []
    comparisons = [("limit_hopping_zero_chain6", "mobile_only"), ("limit_spin_density_zero_rect2x3", "spin_density_only")]
    tolerance = float(gates["zero_coupling_max_abs_difference_db"])
    for case_id, compared_label in comparisons:
        for method, frame in [("exact", exact), ("surrogate", surrogate)]:
            subset = frame[frame.case_id == case_id]
            for keys, static in subset[subset.label == "static_only"].groupby(UNIT, sort=True):
                selector = np.ones(len(subset), dtype=bool)
                for column, value in zip(UNIT, keys): selector &= subset[column].astype(str).to_numpy() == str(value)
                compared = subset.loc[selector & (subset.label == compared_label)]
                merged = static[["time", "xi2_db"]].merge(compared[["time", "xi2_db"]], on="time", suffixes=("_static", "_limit"), validate="one_to_one")
                difference = float(np.max(np.abs(merged.xi2_db_static - merged.xi2_db_limit)))
                limit_rows.append({**dict(zip(UNIT, keys)), "method": method, "comparison_label": compared_label, "max_abs_difference_db": difference, "passed": bool(difference <= tolerance)})
    limits = pd.DataFrame(limit_rows)

    pass_fields = {
        "clean_static_correlation_pass": bool(clean.correlation_pass.all()),
        "clean_static_rmse_pass": bool(clean.rmse_pass.all()),
        "paired_zero_coupling_pass": bool(limits.passed.all()),
        "transport_mapping_pass": bool(mapping["passed"]),
        "all_attempts_completed": bool(manifest["all_attempts_completed"]),
    }
    passed = all(pass_fields.values())
    maximum_calibration_rmse = float(clean.rmse_db.max())
    payload = {
        "stage": "stage5c2gR_calibration_and_validity_tolerance_lock",
        "status": "CALIBRATION_PASSED_AND_TOLERANCES_FROZEN" if passed else "CALIBRATION_FAILED_NO_LOCK",
        "passed": passed,
        "protocol_candidate_sha256": protocol_lock["candidate_sha256"],
        "source_tree_sha256": protocol_lock["candidate_payload"]["source_tree_sha256"],
        "mobility_mapping_lock_sha256": mapping["lock_sha256"],
        "calibration_invariant_lock_sha256": invariant_lock["lock_sha256"],
        "calibration_manifest_sha256": sha256_file(manifest_path),
        "pass_fields": pass_fields,
        "zero_coupling_max_abs_difference_db": tolerance,
        "minimum_time_profile_correlation": float(protocol["validity_gates"]["minimum_time_profile_correlation"]),
        "maximum_clean_static_calibration_rmse_db": maximum_calibration_rmse,
        "maximum_validation_rmse_db": float(protocol["validity_gates"]["maximum_rmse_multiple_of_clean_static_calibration"] * maximum_calibration_rmse),
        "ranking_near_tie_tolerance_db": float(protocol["validity_gates"]["ranking_near_tie_tolerance_db"]),
        "calibration_cases": clean_cases + [case_id for case_id, _ in comparisons],
        "validation_cases_inspected": [],
        "locked_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    payload["lock_sha256"] = sha256_payload(payload)
    output = ROOT / args.out
    output.mkdir(parents=True, exist_ok=True)
    per_unit_frame.to_csv(output / "calibration_per_unit_metrics.csv", index=False)
    clean.to_csv(output / "clean_static_calibration.csv", index=False)
    limits.to_csv(output / "paired_zero_coupling_limits.csv", index=False)
    target = output / ("LOCKED.json" if passed else "FAILED.json")
    target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    if not passed:
        raise SystemExit("mandatory calibration gate failed; no tolerance lock was created and validation remains blocked")


if __name__ == "__main__":
    main()
