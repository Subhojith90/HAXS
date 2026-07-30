from __future__ import annotations
import numpy as np
from .graphs import LatticeGraph

def neighbor_matrix(graph: LatticeGraph, fill: int = -1) -> np.ndarray:
    max_z = max((len(n) for n in graph.neighbors), default=0)
    mat = np.full((graph.n_sites, max_z), fill, dtype=int)
    for i, ns in enumerate(graph.neighbors):
        mat[i, :len(ns)] = ns
    return mat

def active_bonds(graph: LatticeGraph, occupancy: np.ndarray) -> np.ndarray:
    occ = np.asarray(occupancy, dtype=bool)
    if graph.bonds.size == 0:
        return graph.bonds.copy()
    mask = occ[graph.bonds[:, 0]] & occ[graph.bonds[:, 1]]
    return graph.bonds[mask]

def active_bond_count(graph: LatticeGraph, occupancy: np.ndarray) -> int:
    return int(len(active_bonds(graph, occupancy)))

def disrupted_bond_fraction(graph: LatticeGraph, occupancy: np.ndarray) -> float:
    total = max(len(graph.bonds), 1)
    return float(1.0 - active_bond_count(graph, occupancy) / total)
