from __future__ import annotations
import numpy as np
from haxs.utils.rng import rng
from .objectives import evaluate_protocol

def sample_theta(gen: np.random.Generator, bounds: dict, t_max: float) -> dict:
    use_echo = bool(gen.random() < 0.7)
    return {
        "echo_time": float(gen.uniform(bounds.get("echo_min", 0.15), bounds.get("echo_max", 0.9) * t_max)) if use_echo else None,
        "hold_time": float(gen.uniform(bounds.get("hold_min", 0.7) * t_max, bounds.get("hold_max", 1.15) * t_max)),
        "ramp_duration": float(gen.uniform(0.0, bounds.get("ramp_max", 0.5) * t_max)),
        "jz_final": float(gen.uniform(bounds.get("jz_min", -0.2), bounds.get("jz_max", 0.9))),
        "gradient": float(gen.uniform(bounds.get("gradient_min", -0.25), bounds.get("gradient_max", 0.25))),
        "postselect_min_occ": None,
    }

def random_search(config: dict, seeds: list[int], n_candidates: int = 16, seed: int = 1729) -> list[dict[str, object]]:
    gen = rng(seed)
    t_max = float(config.get("dtwa", {}).get("t_max", 1.2))
    bounds = config.get("search_bounds", {})
    results = []
    for _ in range(int(n_candidates)):
        theta = sample_theta(gen, bounds, t_max)
        results.append(evaluate_protocol(config, theta, seeds))
    results.sort(key=lambda r: float(r["objective"]))
    return results
