from __future__ import annotations

def ketterle_like_normalized() -> dict:
    return {
        "units": "J_perp=1 normalized surrogate",
        "lattice": {"shape": [3, 3, 3], "periodic": False},
        "model": {"j_perp": 1.0, "jz": 0.35, "hole_fraction": 0.18, "mobile_eta": 0.55, "lambda_sd": 0.30},
        "dtwa": {"n_traj": 128, "t_max": 1.6, "n_steps": 33},
        "controls": {"enabled": False, "echo_times": [], "gradient": 0.0},
        "claim_status": "not experimental parameters; public-source calibrated values are not asserted",
    }
