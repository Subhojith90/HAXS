from __future__ import annotations

from collections import Counter

import numpy as np


def density_from_occupancy_trajectories(trajectories: np.ndarray) -> np.ndarray:
    values = np.asarray(trajectories, dtype=bool)
    if values.ndim != 3:
        raise ValueError("occupancy trajectories must have shape (paths, times, sites)")
    return np.mean(~values, axis=0, dtype=float)


def mean_squared_displacement(hole_density: np.ndarray, coords: np.ndarray, initial_holes: list[int]) -> np.ndarray:
    density = np.asarray(hole_density, dtype=float)
    positions = np.asarray(coords, dtype=float)
    origins = positions[np.asarray(initial_holes, dtype=int)]
    squared = np.min(np.sum((positions[:, None, :] - origins[None, :, :]) ** 2, axis=2), axis=1)
    normalization = max(1, len(initial_holes))
    return density @ squared / normalization


def return_probability(hole_density: np.ndarray, initial_holes: list[int]) -> np.ndarray:
    density = np.asarray(hole_density, dtype=float)
    return density[:, np.asarray(initial_holes, dtype=int)].sum(axis=1) / max(1, len(initial_holes))


def empirical_configuration_probabilities(occupancy_trajectories: np.ndarray) -> list[dict[tuple[int, ...], float]]:
    trajectories = np.asarray(occupancy_trajectories, dtype=bool)
    output = []
    for time_index in range(trajectories.shape[1]):
        counts = Counter(tuple(np.flatnonzero(~path[time_index]).astype(int)) for path in trajectories)
        output.append({configuration: count / trajectories.shape[0] for configuration, count in counts.items()})
    return output


def configuration_total_variation(exact: list[dict], surrogate: list[dict]) -> np.ndarray:
    values = []
    for left, right in zip(exact, surrogate):
        keys = set(left) | set(right)
        values.append(0.5 * sum(abs(float(left.get(key, 0.0)) - float(right.get(key, 0.0))) for key in keys))
    return np.asarray(values, dtype=float)


def transport_discrepancy(
    exact_density: np.ndarray,
    surrogate_density: np.ndarray,
    coords: np.ndarray,
    initial_holes: list[int],
    exact_configurations: list[dict] | None = None,
    surrogate_configurations: list[dict] | None = None,
) -> dict[str, float | np.ndarray]:
    exact_density = np.asarray(exact_density, dtype=float)
    surrogate_density = np.asarray(surrogate_density, dtype=float)
    exact_msd = mean_squared_displacement(exact_density, coords, initial_holes)
    surrogate_msd = mean_squared_displacement(surrogate_density, coords, initial_holes)
    exact_return = return_probability(exact_density, initial_holes)
    surrogate_return = return_probability(surrogate_density, initial_holes)
    scale = max(1.0, float(np.max(exact_msd)))
    result: dict[str, float | np.ndarray] = {
        "density_l1_by_time": np.sum(np.abs(exact_density - surrogate_density), axis=1) / (2 * max(1, len(initial_holes))),
        "exact_msd": exact_msd,
        "surrogate_msd": surrogate_msd,
        "normalized_msd_error": (exact_msd - surrogate_msd) / scale,
        "exact_return_probability": exact_return,
        "surrogate_return_probability": surrogate_return,
        "return_probability_error": exact_return - surrogate_return,
    }
    if exact_configurations is not None and surrogate_configurations is not None:
        result["configuration_tv_by_time"] = configuration_total_variation(exact_configurations, surrogate_configurations)
    return result

