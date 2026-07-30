from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

def make_decision(validation_passed: bool, mechanism_summary: dict | None, optimization_summary: dict | None, threshold_summary: dict | None) -> dict[str, object]:
    if not validation_passed:
        status = "RED: KILL / PIVOT"
        reason = "validation gates failed"
        scores = {"constructive": 0.0, "mechanism": 0.0, "nogo": 0.0}
    else:
        opt_improvement = float((optimization_summary or {}).get("test_improvement_db", 0.0))
        opt_gap = abs(float((optimization_summary or {}).get("overfitting_gap_db", 999.0)))
        mech_dist = float((mechanism_summary or {}).get("mean_full_vs_static_distance_db", 0.0))
        th = threshold_summary or {}
        thresh_failures = float(th.get("failure_points", 0.0))
        k_boundary = float(th.get("K_boundary", np.nan))
        n_success = int(th.get("n_success", 0) or 0)
        n_failure = int(th.get("n_failure", 0) or 0)
        stable_map = bool(th.get("stable_boolean_map", False))
        constructive = max(0.0, min(1.0, opt_improvement / 3.0)) * (1.0 if opt_gap < 1.0 else 0.35)
        mechanism = max(0.0, min(1.0, mech_dist / 1.0))
        boundary_usable = stable_map and n_success > 0 and n_failure > 0 and np.isfinite(k_boundary) and k_boundary > 0.0
        nogo = max(0.0, min(1.0, thresh_failures / 8.0)) if boundary_usable else 0.0
        scores = {"constructive": constructive, "mechanism": mechanism, "nogo": nogo}
        if constructive > 0.85:
            status = "GREEN: CONSTRUCTIVE PROTOCOL SURVIVES"
            reason = "paper-lite optimizer found robust test-set improvement; still not paper-grade"
        elif mechanism > 0.75 and opt_improvement < 1.0:
            status = "YELLOW: MECHANISM PAPER SURVIVES"
            reason = "mechanism distances are large in the tested surrogate and no robust recovery was found"
        elif nogo > 0.75 and opt_improvement < 1.0:
            status = "BLUE: RESTRICTED NO-GO PAPER SURVIVES"
            reason = "finite grid shows an interpretable, nonzero failure boundary in the tested surrogate"
        else:
            status = "INSUFFICIENT EVIDENCE -- MORE RUNS REQUIRED"
            reason = "laptop paper-lite evidence does not meet green/yellow/blue thresholds"
    return {"status": status, "reason": reason, "route_scores": scores}

def write_decision(path: str | Path, decision: dict) -> None:
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(decision, indent=2), encoding="utf-8")
