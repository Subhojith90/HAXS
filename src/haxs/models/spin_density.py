from __future__ import annotations
import numpy as np
from haxs.lattice.graphs import LatticeGraph

def spin_density_field(graph: LatticeGraph, occupancy: np.ndarray, lambda_sd: float) -> np.ndarray:
    occ = np.asarray(occupancy, dtype=bool)
    holes = (~occ).astype(float)
    field = np.zeros(graph.n_sites, dtype=float)
    for i, ns in enumerate(graph.neighbors):
        field[i] = float(lambda_sd) * sum(holes[j] for j in ns)
    return field

def field_autocorrelation(fields: np.ndarray) -> np.ndarray:
    x = np.asarray(fields, dtype=float)
    if x.ndim == 1:
        x = x[:, None]
    x = x - np.mean(x, axis=0, keepdims=True)
    denom = np.sum(x * x)
    if denom <= 1e-15:
        return np.ones(x.shape[0])
    vals = []
    for lag in range(x.shape[0]):
        vals.append(float(np.sum(x[:x.shape[0]-lag] * x[lag:]) / denom))
    return np.array(vals)

def hole_spin_covariance(occupancy: np.ndarray, spin_z: np.ndarray) -> float:
    holes = (~np.asarray(occupancy, dtype=bool)).astype(float)
    z = np.asarray(spin_z, dtype=float)
    if holes.size != z.size or holes.size == 0:
        return 0.0
    return float(np.mean((holes - holes.mean()) * (z - z.mean())))

def pair_correction_jz(jz: float, occupancy: np.ndarray, lambda_sd2: float = 0.0) -> float:
    occ = np.asarray(occupancy, dtype=float)
    return float(jz + lambda_sd2 * np.mean(occ))
