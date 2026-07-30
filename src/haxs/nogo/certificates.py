from __future__ import annotations
import pandas as pd

def restricted_nogo_certificate(threshold_df: pd.DataFrame) -> dict[str, object]:
    if threshold_df.empty:
        return {"certificate": "none", "reason": "empty threshold scan"}
    stable = threshold_df.groupby(["dimension", "mobile_eta", "lambda_sd"])["success_target"].nunique().max() <= 2
    failures = int((~threshold_df["success_target"]).sum())
    return {"certificate": "empirical restricted threshold evidence", "stable_boolean_map": bool(stable), "failure_points": failures, "scope": "finite sizes, stochastic-hole surrogate, global no-control/echo-class defaults"}
