from __future__ import annotations
import numpy as np

def collective_spin_from_trajectories(spins: np.ndarray, occupancy: np.ndarray | None = None) -> np.ndarray:
    arr = np.asarray(spins, dtype=float)
    if occupancy is None:
        return np.sum(arr, axis=1)
    occ = np.asarray(occupancy, dtype=float)
    if occ.ndim == 1:
        return np.sum(arr * occ[None, :, None], axis=1)
    return np.einsum("tn,knc->tc", occ, arr)

def mean_and_covariance(samples: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    x = np.asarray(samples, dtype=float)
    if x.ndim != 2 or x.shape[0] == 0:
        return np.zeros(3), np.eye(3) * np.nan
    mean = np.mean(x, axis=0)
    centered = x - mean
    cov = centered.T @ centered / max(x.shape[0] - 1, 1)
    return mean, 0.5 * (cov + cov.T)

def spin_length(mean_spin: np.ndarray, n_eff: float) -> float:
    if n_eff <= 0:
        return 0.0
    return float(2.0 * np.linalg.norm(mean_spin) / n_eff)
