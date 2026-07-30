from __future__ import annotations

import numpy as np
import pandas as pd


def balanced_cube(frame: pd.DataFrame, value: str) -> np.ndarray:
    occupancies = sorted(frame.occupancy_idx.unique()); paths = sorted(frame.path_idx.unique()); phases = sorted(frame.phase_idx.unique())
    cube = np.empty((len(occupancies), len(paths), len(phases)), dtype=float)
    for oi, occupancy in enumerate(occupancies):
        for pi, path in enumerate(paths):
            subset = frame[(frame.occupancy_idx == occupancy) & (frame.path_idx == path)].sort_values("phase_idx")
            if list(subset.phase_idx) != phases: raise ValueError("hierarchical validity requires a complete balanced occupancy/path/phase grid")
            cube[oi, pi] = subset[value].to_numpy(float)
    return cube


def nested_bootstrap_interval(frame: pd.DataFrame, value: str, replicates: int, seed: int, confidence: float = 0.95) -> dict[str, float]:
    cube = balanced_cube(frame, value); generator = np.random.default_rng(int(seed)); samples = np.empty(int(replicates), dtype=float)
    o, p, b = cube.shape
    for index in range(int(replicates)):
        oi = generator.integers(0, o, size=o); pi = generator.integers(0, p, size=(o, p)); bi = generator.integers(0, b, size=(o, p, b))
        samples[index] = cube[oi[:, None, None], pi[:, :, None], bi].mean()
    alpha = 1.0 - float(confidence)
    return {"mean": float(cube.mean()), "standard_error": float(samples.std(ddof=1)), "ci_low": float(np.quantile(samples, alpha / 2)), "ci_high": float(np.quantile(samples, 1 - alpha / 2)), "replicates": int(replicates), "confidence": float(confidence)}


def joint_nested_bootstrap(frame: pd.DataFrame, value_columns: list[str], replicates: int, seed: int, confidence: float = 0.95) -> dict:
    cubes = [balanced_cube(frame, column) for column in value_columns]
    if len({cube.shape for cube in cubes}) != 1: raise ValueError("joint hierarchy shapes differ")
    generator = np.random.default_rng(int(seed)); samples = np.empty((int(replicates), len(cubes)), dtype=float); o, p, b = cubes[0].shape
    for index in range(int(replicates)):
        oi = generator.integers(0, o, size=o); pi = generator.integers(0, p, size=(o, p)); bi = generator.integers(0, b, size=(o, p, b))
        for column, cube in enumerate(cubes): samples[index, column] = cube[oi[:, None, None], pi[:, :, None], bi].mean()
    means = np.asarray([cube.mean() for cube in cubes]); centered_max = np.max(np.abs(samples - means[None, :]), axis=1); critical = float(np.quantile(centered_max, confidence))
    return {"columns": value_columns, "means": means.tolist(), "simultaneous_low": (means - critical).tolist(), "simultaneous_high": (means + critical).tolist(), "critical_deviation": critical, "bootstrap_covariance": np.cov(samples, rowvar=False).tolist(), "replicates": int(replicates), "confidence": float(confidence)}


def evaluate_metric_groups(frame: pd.DataFrame, replicates: int, seed: int, confidence: float = 0.95) -> pd.DataFrame:
    rows = []
    for index, (keys, group) in enumerate(frame.groupby(["case_id", "label", "metric"], sort=True)):
        result = nested_bootstrap_interval(group, "value", replicates, seed + index, confidence)
        direction = str(group.gate_direction.iloc[0]); threshold = float(group.gate_threshold.iloc[0])
        passed = result["ci_low"] >= threshold if direction == "minimum" else result["ci_high"] <= threshold
        rows.append({"case_id": keys[0], "label": keys[1], "metric": keys[2], "gate_direction": direction, "gate_threshold": threshold, **result, "passed": bool(passed)})
    return pd.DataFrame(rows)

