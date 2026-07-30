from __future__ import annotations
import numpy as np
import pandas as pd

def summarize_overfitting(train_result: dict, test_result: dict) -> dict[str, float]:
    train = float(train_result.get("mean_xi2_db", np.nan))
    test = float(test_result.get("mean_xi2_db", np.nan))
    return {"train_xi2_db": train, "test_xi2_db": test, "overfitting_gap_db": float(test - train)}

def finals_to_dataframe(results: list[dict], label: str) -> pd.DataFrame:
    rows = []
    for r in results:
        for f in r.get("finals", []):
            d = dict(f); d["label"] = label; d["objective"] = float(r.get("objective", np.nan)); rows.append(d)
    return pd.DataFrame(rows)
