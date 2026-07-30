from __future__ import annotations

import numpy as np
from scipy.optimize import linear_sum_assignment

from haxs.lattice.graphs import LatticeGraph


def _occupied_degrees(graph: LatticeGraph, occupancy: np.ndarray) -> np.ndarray:
    occ = np.asarray(occupancy, dtype=bool)
    return np.asarray([sum(bool(occ[j]) for j in graph.neighbors[i]) for i in range(graph.n_sites) if occ[i]], dtype=float)


def largest_occupied_component(graph: LatticeGraph, occupancy: np.ndarray) -> int:
    occ = np.asarray(occupancy, dtype=bool)
    unseen = {int(i) for i in np.flatnonzero(occ)}
    largest = 0
    while unseen:
        root = unseen.pop()
        stack = [root]
        size = 1
        while stack:
            node = stack.pop()
            for neighbor in graph.neighbors[node]:
                if neighbor in unseen and occ[neighbor]:
                    unseen.remove(neighbor)
                    stack.append(int(neighbor))
                    size += 1
        largest = max(largest, size)
    return int(largest)


def _boundary_mask(graph: LatticeGraph) -> np.ndarray:
    shape = np.asarray(graph.shape, dtype=int)
    return np.any((graph.coords == 0) | (graph.coords == shape[None, :] - 1), axis=1)


def topology_descriptors(graph: LatticeGraph, occupancy: np.ndarray) -> dict[str, float | int | bool]:
    occ = np.asarray(occupancy, dtype=bool)
    holes = ~occ
    n_occupied = int(occ.sum())
    n_holes = int(holes.sum())
    active_bonds = int(sum(bool(occ[a] and occ[b]) for a, b in graph.bonds))
    hole_bonds = int(sum(bool(holes[a] and holes[b]) for a, b in graph.bonds))
    degrees = _occupied_degrees(graph, occ)
    largest = largest_occupied_component(graph, occ)
    boundary = _boundary_mask(graph)
    return {
        "n_holes": n_holes,
        "active_bonds": active_bonds,
        "largest_connected_component": largest,
        "largest_connected_component_fraction": float(largest / n_occupied) if n_occupied else 0.0,
        "occupied_graph_connected": bool(largest == n_occupied and n_occupied > 0),
        "occupied_degree_mean": float(degrees.mean()) if degrees.size else 0.0,
        "occupied_degree_variance": float(degrees.var()) if degrees.size else 0.0,
        "occupied_degree_second_moment": float(np.mean(degrees**2)) if degrees.size else 0.0,
        "hole_adjacent_pairs": hole_bonds,
        "hole_clustering_fraction": float(hole_bonds / max(1, n_holes * (n_holes - 1) / 2)),
        "boundary_hole_fraction": float(np.mean(boundary[holes])) if n_holes else 0.0,
    }


def random_walk_displacement(graph: LatticeGraph, occupancy_trajectory: np.ndarray) -> dict[str, float]:
    trajectory = np.asarray(occupancy_trajectory, dtype=bool)
    if trajectory.ndim != 2 or trajectory.shape[0] == 0:
        return {"random_walk_displacement_mean": 0.0, "random_walk_displacement_rms": 0.0}
    initial = np.flatnonzero(~trajectory[0])
    final = np.flatnonzero(~trajectory[-1])
    if len(initial) == 0 or len(initial) != len(final):
        return {"random_walk_displacement_mean": float("nan"), "random_walk_displacement_rms": float("nan")}
    distances = np.linalg.norm(graph.coords[initial, None, :] - graph.coords[None, final, :], axis=2)
    rows, cols = linear_sum_assignment(distances)
    matched = distances[rows, cols]
    return {
        "random_walk_displacement_mean": float(matched.mean()),
        "random_walk_displacement_rms": float(np.sqrt(np.mean(matched**2))),
    }

