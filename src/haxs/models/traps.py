from __future__ import annotations
import numpy as np
from haxs.lattice.graphs import LatticeGraph

def harmonic_profile(graph: LatticeGraph, strength: float = 0.0) -> np.ndarray:
    center = (np.array(graph.shape) - 1.0) / 2.0
    r2 = np.sum((graph.coords - center) ** 2, axis=1)
    return float(strength) * r2

def trap_biased_hole_probabilities(graph: LatticeGraph, mean_hole_fraction: float, strength: float = 2.0) -> np.ndarray:
    prof = harmonic_profile(graph, 1.0)
    if np.max(prof) > 0:
        weights = 1.0 + float(strength) * prof / np.max(prof)
    else:
        weights = np.ones(graph.n_sites)
    probs = float(mean_hole_fraction) * weights / np.mean(weights)
    return np.clip(probs, 0.0, 0.95)
