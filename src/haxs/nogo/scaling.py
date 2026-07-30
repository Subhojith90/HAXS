from __future__ import annotations
import numpy as np
import pandas as pd

def k_hsd_boundary_fit(df: pd.DataFrame) -> dict[str, float]:
    if df.empty or "K_hsd" not in df:
        return {"K_boundary": float("nan"), "n_success": 0, "n_failure": 0}
    success = df[df["success_target"]]
    failure = df[~df["success_target"]]
    if success.empty or failure.empty:
        return {"K_boundary": float("nan"), "n_success": int(len(success)), "n_failure": int(len(failure))}
    boundary = 0.5 * (float(success["K_hsd"].max()) + float(failure["K_hsd"].min()))
    return {"K_boundary": boundary, "n_success": int(len(success)), "n_failure": int(len(failure))}
