from __future__ import annotations
import numpy as np
from haxs.lattice.neighbours import active_bond_count

def finite_difference_sensitivity(y_plus: float, y_minus: float, delta: float) -> float:
    if abs(delta) < 1e-15:
        return 0.0
    return float((np.log(max(y_plus, 1e-300)) - np.log(max(y_minus, 1e-300))) / (2.0 * delta))

def bootstrap_ci(values, seed: int = 1729, n_boot: int = 400, alpha: float = 0.10) -> tuple[float, float, float]:
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    if x.size == 0:
        return float("nan"), float("nan"), float("nan")
    gen = np.random.default_rng(seed)
    means = np.array([np.mean(gen.choice(x, size=x.size, replace=True)) for _ in range(int(n_boot))])
    lo, hi = np.quantile(means, [alpha/2, 1-alpha/2])
    return float(np.mean(x)), float(lo), float(hi)

def mechanism_distance(curve_a, curve_b) -> float:
    a = np.asarray(curve_a, dtype=float); b = np.asarray(curve_b, dtype=float)
    n = min(a.size, b.size)
    if n == 0:
        return 0.0
    return float(np.sqrt(np.mean((a[:n] - b[:n]) ** 2)))

def hole_scrambling_number(hole_fraction: float, eta: float, lambda_sd: float, coordination: float, t: float) -> float:
    return float(hole_fraction * coordination * (1.0 - np.exp(-max(eta, 0.0) * max(t, 0.0))) * (1.0 + lambda_sd**2) * max(t, 0.0))

def active_bond_disruption(graph, occupancy) -> float:
    total = max(len(graph.bonds), 1)
    return float(1.0 - active_bond_count(graph, occupancy) / total)

def curve_sensitivity_table(curves: dict[str, np.ndarray]) -> dict[str, float]:
    names = list(curves)
    out: dict[str, float] = {}
    for i, a in enumerate(names):
        for b in names[i+1:]:
            out[f"distance_{a}_vs_{b}"] = mechanism_distance(curves[a], curves[b])
    return out
