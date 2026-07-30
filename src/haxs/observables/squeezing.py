from __future__ import annotations
import numpy as np
from haxs.utils.math import xi2_to_db

def perpendicular_basis(vec: np.ndarray) -> np.ndarray:
    v = np.asarray(vec, dtype=float)
    norm = np.linalg.norm(v)
    if norm < 1e-14:
        return np.eye(3)[:2]
    e0 = v / norm
    trial = np.array([1.0, 0.0, 0.0]) if abs(e0[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    e1 = trial - np.dot(trial, e0) * e0
    e1 /= max(np.linalg.norm(e1), 1e-14)
    e2 = np.cross(e0, e1)
    e2 /= max(np.linalg.norm(e2), 1e-14)
    return np.vstack([e1, e2])

def min_perpendicular_variance(mean_spin: np.ndarray, covariance: np.ndarray) -> float:
    cov = np.asarray(covariance, dtype=float)
    if cov.shape != (3, 3) or not np.all(np.isfinite(cov)):
        return float("inf")
    basis = perpendicular_basis(mean_spin)
    proj = basis @ (0.5 * (cov + cov.T)) @ basis.T
    evals = np.linalg.eigvalsh(0.5 * (proj + proj.T))
    return float(max(np.min(evals), 0.0))

def wineland_squeezing(mean_spin: np.ndarray, covariance: np.ndarray, n_eff: float) -> dict[str, float]:
    mean_spin = np.asarray(mean_spin, dtype=float)
    spin_norm2 = float(np.dot(mean_spin, mean_spin))
    if n_eff <= 1 or spin_norm2 < 1e-14:
        return {"xi2": float("inf"), "xi2_db": float("inf"), "min_var": float("inf"), "spin_norm": float(np.sqrt(max(spin_norm2, 0.0)))}
    min_var = min_perpendicular_variance(mean_spin, covariance)
    xi2 = float(n_eff * min_var / spin_norm2) if np.isfinite(min_var) else float("inf")
    return {"xi2": xi2, "xi2_db": xi2_to_db(xi2), "min_var": min_var, "spin_norm": float(np.sqrt(spin_norm2))}

def css_reference(n_eff: int) -> dict[str, float]:
    mean = np.array([n_eff / 2.0, 0.0, 0.0])
    cov = np.diag([0.0, n_eff / 4.0, n_eff / 4.0])
    return wineland_squeezing(mean, cov, n_eff)
