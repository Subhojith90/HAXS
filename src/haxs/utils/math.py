from __future__ import annotations
import numpy as np

def safe_divide(a: float, b: float, default: float = float("inf")) -> float:
    if not np.isfinite(a) or not np.isfinite(b) or abs(b) < 1e-15:
        return float(default)
    return float(a / b)

def xi2_to_db(xi2: float) -> float:
    x = max(float(xi2), 1e-300)
    return float(10.0 * np.log10(x))

def db_to_xi2(db: float) -> float:
    return float(10.0 ** (float(db) / 10.0))

def finite_or(value: float, default: float) -> float:
    return float(value) if np.isfinite(value) else float(default)

def normalize_rows(arr: np.ndarray, target_norm: float = 0.5) -> np.ndarray:
    norms = np.linalg.norm(arr, axis=-1, keepdims=True)
    scale = np.ones_like(norms)
    mask = norms > 1e-14
    scale[mask] = float(target_norm) / norms[mask]
    return arr * scale
