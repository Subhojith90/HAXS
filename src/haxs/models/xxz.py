from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from haxs.lattice.graphs import LatticeGraph

@dataclass(frozen=True)
class XXZParameters:
    j_perp: float = 1.0
    jz: float = 0.35
    fields: np.ndarray | None = None

def normalized_xxz(jz: float = 0.35, n_sites: int | None = None) -> XXZParameters:
    fields = np.zeros(n_sites, dtype=float) if n_sites is not None else None
    return XXZParameters(j_perp=1.0, jz=float(jz), fields=fields)

def gradient_fields(graph: LatticeGraph, gradient: float = 0.0, axis: int = 0) -> np.ndarray:
    coords = graph.coords[:, int(axis)] if graph.n_sites else np.zeros(0)
    centered = coords - np.mean(coords) if len(coords) else coords
    return float(gradient) * centered.astype(float)

def pair_energy_components(spins: np.ndarray, bonds: np.ndarray, j_perp: float, jz: float) -> float:
    if len(bonds) == 0:
        return 0.0
    si = spins[bonds[:, 0]]; sj = spins[bonds[:, 1]]
    e = j_perp * np.sum(si[:, 0] * sj[:, 0] + si[:, 1] * sj[:, 1]) + jz * np.sum(si[:, 2] * sj[:, 2])
    return float(e)
