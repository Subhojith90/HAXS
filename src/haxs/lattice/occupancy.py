from __future__ import annotations
from pathlib import Path
import numpy as np
from .graphs import LatticeGraph
from .neighbours import active_bond_count
from haxs.utils.rng import rng

def sample_bernoulli(n_sites: int, hole_fraction: float, seed: int | None = None) -> np.ndarray:
    gen = rng(seed)
    occ = gen.random(int(n_sites)) >= float(hole_fraction)
    return occ.astype(bool)

def sample_fixed_count(n_sites: int, n_holes: int, seed: int | None = None) -> np.ndarray:
    gen = rng(seed)
    n_sites = int(n_sites); n_holes = int(max(0, min(n_holes, n_sites)))
    occ = np.ones(n_sites, dtype=bool)
    if n_holes:
        holes = gen.choice(n_sites, size=n_holes, replace=False)
        occ[holes] = False
    return occ

def sample_clustered(graph: LatticeGraph, n_holes: int, seed: int | None = None) -> np.ndarray:
    gen = rng(seed)
    occ = np.ones(graph.n_sites, dtype=bool)
    n_holes = int(max(0, min(n_holes, graph.n_sites)))
    if n_holes == 0:
        return occ
    start = int(gen.integers(0, graph.n_sites))
    holes = {start}
    frontier = [start]
    while len(holes) < n_holes and frontier:
        current = frontier.pop(0)
        ns = list(graph.neighbors[current])
        gen.shuffle(ns)
        for nb in ns:
            if len(holes) >= n_holes:
                break
            if nb not in holes:
                holes.add(nb); frontier.append(nb)
    while len(holes) < n_holes:
        holes.add(int(gen.integers(0, graph.n_sites)))
    occ[list(holes)] = False
    return occ

def sample_trap_biased(graph: LatticeGraph, hole_fraction: float, bias_strength: float = 2.0, seed: int | None = None) -> np.ndarray:
    gen = rng(seed)
    center = (np.array(graph.shape) - 1) / 2.0
    r2 = np.sum((graph.coords - center) ** 2, axis=1)
    if np.max(r2) > 0:
        weights = 1.0 + bias_strength * r2 / np.max(r2)
    else:
        weights = np.ones(graph.n_sites)
    probs = np.clip(hole_fraction * weights / np.mean(weights), 0.0, 0.95)
    return (gen.random(graph.n_sites) >= probs).astype(bool)

def occupancy_stats(graph: LatticeGraph, occupancy: np.ndarray) -> dict[str, float]:
    occ = np.asarray(occupancy, dtype=bool)
    return {
        "n_sites": int(graph.n_sites),
        "n_occ": int(np.sum(occ)),
        "hole_fraction_realized": float(1.0 - np.mean(occ)) if graph.n_sites else 1.0,
        "active_bonds": int(active_bond_count(graph, occ)),
        "total_bonds": int(len(graph.bonds)),
    }

def save_occupancy(path: str | Path, occupancy: np.ndarray) -> None:
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    np.savetxt(p, np.asarray(occupancy, dtype=int), fmt="%d")

def load_occupancy(path: str | Path) -> np.ndarray:
    return np.loadtxt(path, dtype=int).astype(bool)
