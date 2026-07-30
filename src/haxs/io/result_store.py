from __future__ import annotations
from pathlib import Path
import json
import pandas as pd
from haxs.io.hashes import hash_dict

def ensure_dir(path: str | Path) -> Path:
    p = Path(path); p.mkdir(parents=True, exist_ok=True); return p

def save_json(path: str | Path, data: dict) -> None:
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))

def save_dataframe(path: str | Path, df: pd.DataFrame, config: dict | None = None) -> None:
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    out = df.copy()
    if config is not None and "config_hash" not in out.columns:
        out["config_hash"] = hash_dict(config)
    out.to_csv(p, index=False)

def read_dataframe(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(path)
