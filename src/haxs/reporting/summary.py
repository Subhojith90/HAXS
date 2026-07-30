from __future__ import annotations
from pathlib import Path
import pandas as pd

def load_if_exists(path: str | Path) -> pd.DataFrame:
    p = Path(path)
    return pd.read_csv(p) if p.exists() else pd.DataFrame()

def scalar_summary(df: pd.DataFrame, column: str) -> dict[str, float]:
    if df.empty or column not in df:
        return {"mean": float("nan"), "min": float("nan"), "max": float("nan")}
    x = df[column].dropna().astype(float)
    return {"mean": float(x.mean()), "min": float(x.min()), "max": float(x.max())}
