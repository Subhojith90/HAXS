from __future__ import annotations

def default_run_config() -> dict:
    return {
        "seed": 1729,
        "level": "smoke",
        "lattice": {"shape": [8], "periodic": False},
        "model": {"j_perp": 1.0, "jz": 0.35, "hole_fraction": 0.0, "mobile_eta": 0.0, "lambda_sd": 0.0},
        "dtwa": {"n_traj": 64, "t_max": 1.2, "n_steps": 25},
        "controls": {"enabled": False, "echo_times": [], "gradient": 0.0, "jz_final": None, "ramp_duration": 0.0},
    }

def merge_dicts(base: dict, override: dict) -> dict:
    out = dict(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = merge_dicts(out[key], value)
        else:
            out[key] = value
    return out
