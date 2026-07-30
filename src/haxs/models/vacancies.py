from __future__ import annotations
import numpy as np
from haxs.lattice.graphs import LatticeGraph
from haxs.lattice.occupancy import sample_bernoulli, sample_fixed_count, sample_clustered, sample_trap_biased, occupancy_stats

VACANCY_MODES = ("bernoulli", "fixed", "clustered", "trap_biased")

def make_vacancies(graph: LatticeGraph, hole_fraction: float, seed: int, mode: str = "bernoulli", fixed_hole_count: int | None = None) -> np.ndarray:
    if mode == "bernoulli":
        return sample_bernoulli(graph.n_sites, hole_fraction, seed)
    n_holes = int(round(hole_fraction * graph.n_sites)) if fixed_hole_count is None else int(fixed_hole_count)
    if mode == "fixed":
        return sample_fixed_count(graph.n_sites, n_holes, seed)
    if mode == "clustered":
        return sample_clustered(graph, n_holes, seed)
    if mode == "trap_biased":
        return sample_trap_biased(graph, hole_fraction, seed=seed)
    raise ValueError(f"unknown vacancy mode {mode}")

def vacancy_summary(graph: LatticeGraph, occupancy: np.ndarray) -> dict[str, float]:
    return occupancy_stats(graph, occupancy)
