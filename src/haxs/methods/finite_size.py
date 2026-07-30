from __future__ import annotations
import numpy as np
import pandas as pd

def finite_size_slope(table: pd.DataFrame, x_col: str = "N_eff", y_col: str = "xi2") -> dict[str, float]:
    df = table[[x_col, y_col]].dropna()
    df = df[(df[x_col] > 0) & (df[y_col] > 0)]
    if len(df) < 2:
        return {"slope_loglog": float("nan"), "intercept": float("nan"), "n_points": int(len(df))}
    x = np.log(df[x_col].to_numpy(float)); y = np.log(df[y_col].to_numpy(float))
    slope, intercept = np.polyfit(x, y, 1)
    return {"slope_loglog": float(slope), "intercept": float(intercept), "n_points": int(len(df))}

def summarize_by_size(table: pd.DataFrame) -> pd.DataFrame:
    return table.groupby("N_eff", dropna=False).agg(xi2_mean=("xi2", "mean"), xi2_std=("xi2", "std"), n=("xi2", "count")).reset_index()
