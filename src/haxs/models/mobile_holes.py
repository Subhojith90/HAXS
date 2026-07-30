from __future__ import annotations
import numpy as np
from haxs.lattice.graphs import LatticeGraph
from haxs.utils.rng import rng

def hole_positions_from_occupancy(occupancy: np.ndarray) -> list[int]:
    return [int(i) for i in np.where(~np.asarray(occupancy, dtype=bool))[0]]

def random_walk_holes(graph: LatticeGraph, initial_holes: list[int], n_steps: int, hop_probability: float, seed: int | None = None) -> np.ndarray:
    gen = rng(seed)
    holes = [int(h) for h in initial_holes]
    n_holes = len(holes)
    out = np.empty((int(n_steps), n_holes), dtype=int)
    occupied_by_hole = set(holes)
    for t in range(int(n_steps)):
        out[t] = holes
        for k, h in enumerate(list(holes)):
            if gen.random() >= hop_probability:
                continue
            candidates = [n for n in graph.neighbors[h] if n not in occupied_by_hole]
            if candidates:
                new_h = int(gen.choice(candidates))
                occupied_by_hole.remove(h)
                occupied_by_hole.add(new_h)
                holes[k] = new_h
    return out

def occupancy_trajectory_from_holes(n_sites: int, hole_traj: np.ndarray) -> np.ndarray:
    occ = np.ones((hole_traj.shape[0], int(n_sites)), dtype=bool)
    for t, holes in enumerate(hole_traj):
        occ[t, holes.astype(int)] = False
    return occ

def mobile_occupancy_trajectory(graph: LatticeGraph, initial_occupancy: np.ndarray, n_steps: int, eta: float, dt: float, seed: int | None = None) -> np.ndarray:
    holes = hole_positions_from_occupancy(initial_occupancy)
    if len(holes) == 0:
        return np.repeat(np.asarray(initial_occupancy, dtype=bool)[None, :], int(n_steps), axis=0)
    hop_p = float(np.clip(eta * dt, 0.0, 1.0))
    if hop_p <= 0.0:
        return np.repeat(np.asarray(initial_occupancy, dtype=bool)[None, :], int(n_steps), axis=0)
    traj = random_walk_holes(graph, holes, n_steps, hop_p, seed)
    return occupancy_trajectory_from_holes(graph.n_sites, traj)

def mobility_summary(occ_traj: np.ndarray) -> dict[str, float]:
    holes = ~np.asarray(occ_traj, dtype=bool)
    moved = float(np.mean(np.any(holes != holes[0:1], axis=1))) if len(holes) else 0.0
    return {"n_steps": int(len(occ_traj)), "n_holes": int(np.sum(holes[0])) if len(holes) else 0, "fraction_steps_changed": moved}
