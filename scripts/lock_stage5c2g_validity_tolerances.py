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
from stage5c2g_common import assert_protocol_locked, load_yaml, sha256_payload


def comparison(exact: pd.DataFrame, surrogate: pd.DataFrame) -> tuple[float, float]:
    merged = exact[["time", "xi2_db"]].merge(surrogate[["time", "xi2_db"]], on="time", suffixes=("_exact", "_surrogate"), validate="one_to_one")
    correlation = float(np.corrcoef(merged.xi2_db_exact, merged.xi2_db_surrogate)[0, 1])
    rmse = float(np.sqrt(np.mean((merged.xi2_db_exact - merged.xi2_db_surrogate) ** 2)))
    return correlation, rmse


def main() -> None:
    raise SystemExit("REJECTED LEGACY ROUTE: Stage 5C.2G tolerance locking is disabled")
    parser = argparse.ArgumentParser()
    parser.add_argument("--calibration", default="results/stage5c2g/calibration")
    parser.add_argument("--protocol", default="configs/stage5c2g/protocol.yaml")
    parser.add_argument("--out", default="results/stage5c2g/validity_tolerances")
    args = parser.parse_args()
    protocol_lock = assert_protocol_locked()
    protocol = load_yaml(args.protocol)["stage5c2g_protocol"]
    root = ROOT / args.calibration
    exact = pd.read_csv(root / "stage5c2g_exact_curves.csv")
    surrogate = pd.read_csv(root / "stage5c2g_surrogate_curves.csv")
    rows = []
    for case_id in ["cal_chain6_one_hole", "cal_rect2x3_one_hole"]:
        exact_case = exact[(exact.case_id == case_id) & (exact.label == "static_only")]
        surrogate_case = surrogate[(surrogate.case_id == case_id) & (surrogate.label == "static_only")]
        correlation, rmse = comparison(exact_case, surrogate_case)
        rows.append({"case_id": case_id, "correlation": correlation, "rmse_db": rmse})
    limit_rows = []
    for case_id, comparison_label in [("limit_hopping_zero_chain6", "mobile_only"), ("limit_spin_density_zero_rect2x3", "spin_density_only")]:
        for method, frame in [("exact", exact), ("surrogate", surrogate)]:
            subset = frame[frame.case_id == case_id]
            static = subset[subset.label == "static_only"][["time", "xi2_db"]]
            compared = subset[subset.label == comparison_label][["time", "xi2_db"]]
            merged = static.merge(compared, on="time", suffixes=("_static", "_limit"), validate="one_to_one")
            max_error = float(np.max(np.abs(merged.xi2_db_static - merged.xi2_db_limit)))
            limit_rows.append({"case_id": case_id, "method": method, "comparison_label": comparison_label, "max_abs_difference_db": max_error, "passed": max_error <= 1e-10})
    maximum_calibration_rmse = float(max(row["rmse_db"] for row in rows))
    payload = {
        "stage": "stage5c2g_validity_tolerance_lock",
        "status": "LOCKED_AFTER_CALIBRATION_BEFORE_VALIDATION",
        "locked_at_utc": datetime.now(timezone.utc).isoformat(),
        "protocol_candidate_sha256": protocol_lock["candidate_sha256"],
        "minimum_time_profile_correlation": float(protocol["validity_gates"]["minimum_time_profile_correlation"]),
        "clean_static_calibration": rows,
        "calibration_rmse_aggregation": "maximum_across_preregistered_clean_static_calibration_cases",
        "maximum_clean_static_calibration_rmse_db": maximum_calibration_rmse,
        "maximum_validation_rmse_db": float(protocol["validity_gates"]["maximum_rmse_multiple_of_clean_static_calibration"] * maximum_calibration_rmse),
        "zero_coupling_limit_checks": limit_rows,
        "zero_coupling_limits_pass": bool(all(row["passed"] for row in limit_rows)),
    }
    payload["tolerance_lock_sha256"] = sha256_payload(payload)
    output = ROOT / args.out
    output.mkdir(parents=True, exist_ok=True)
    (output / "LOCKED.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    pd.DataFrame(rows).to_csv(output / "calibration_comparison.csv", index=False)
    pd.DataFrame(limit_rows).to_csv(output / "zero_coupling_limits.csv", index=False)
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
