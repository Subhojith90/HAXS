from __future__ import annotations
import numpy as np

def connected_collective_covariance(spins: np.ndarray, occupancy: np.ndarray | None = None) -> np.ndarray:
    from .collective_spin import collective_spin_from_trajectories, mean_and_covariance
    samples = collective_spin_from_trajectories(spins, occupancy)
    return mean_and_covariance(samples)[1]

def nearest_neighbor_zz(spins: np.ndarray, bonds: np.ndarray, occupancy: np.ndarray | None = None) -> float:
    arr = np.asarray(spins, dtype=float)
    if len(bonds) == 0:
        return 0.0
    vals = arr[:, bonds[:,0], 2] * arr[:, bonds[:,1], 2]
    if occupancy is not None:
        occ = np.asarray(occupancy, dtype=bool)
        vals = vals[:, occ[bonds[:,0]] & occ[bonds[:,1]]]
    return float(np.mean(vals)) if vals.size else 0.0

def structure_factor_zero(samples: np.ndarray) -> float:
    x = np.asarray(samples, dtype=float)
    return float(np.mean(np.sum(x, axis=1) ** 2)) if x.size else 0.0
