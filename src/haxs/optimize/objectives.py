from __future__ import annotations
import numpy as np
from haxs.lattice.graphs import hypercubic_lattice
from haxs.methods.dtwa import run_dtwa
from haxs.models.controls import ControlProtocol
from haxs.observables.resource_accounting import account_resources

def protocol_from_theta(theta: dict, jz_initial: float, t_max: float) -> ControlProtocol:
    echo = [] if theta.get("echo_time", None) is None else [float(theta["echo_time"])]
    return ControlProtocol(
        enabled=True,
        echo_times=tuple(e for e in echo if 0.0 < e < t_max),
        gradient=float(theta.get("gradient", 0.0)),
        jz_initial=float(jz_initial),
        jz_final=float(theta.get("jz_final", jz_initial)),
        ramp_duration=float(theta.get("ramp_duration", 0.0)),
        final_time=float(theta.get("hold_time", t_max)),
        postselect_min_occ=theta.get("postselect_min_occ", None),
    )

def evaluate_protocol(config: dict, theta: dict, seeds: list[int]) -> dict[str, object]:
    shape = tuple(config.get("lattice", {}).get("shape", [3, 3, 3]))
    graph = hypercubic_lattice(shape, config.get("lattice", {}).get("periodic", False))
    model = config.get("model", {})
    dtwa = config.get("dtwa", {})
    t_max = float(theta.get("hold_time", dtwa.get("t_max", 1.2)))
    times = np.linspace(0.0, t_max, int(dtwa.get("n_steps", 25)))
    ctrl = protocol_from_theta(theta, float(model.get("jz", 0.35)), t_max)
    finals = []
    resources = []
    for s in seeds:
        res = run_dtwa(graph, times, j_perp=float(model.get("j_perp", 1.0)), jz=float(model.get("jz", 0.35)), hole_fraction=float(model.get("hole_fraction", 0.18)), mobile_eta=float(model.get("mobile_eta", 0.4)), lambda_sd=float(model.get("lambda_sd", 0.25)), n_traj=int(dtwa.get("n_traj", 64)), seed=int(s), control=ctrl)
        data = res["data"]
        best_idx = int(np.nanargmin(data[:, 4]))
        final = {"seed": int(s), "xi2_min": float(data[best_idx, 4]), "xi2_db_min": float(data[best_idx, 5]), "spin_length_at_min": float(data[best_idx, 7]), "time_at_min": float(data[best_idx, 0]), "N_eff": float(data[best_idx, 8])}
        finals.append(final)
        resources.append(account_resources(graph.n_sites, [data[best_idx, 8]], data[best_idx, 4], data[best_idx, 7]).as_dict())
    xi_vals = np.array([f["xi2_min"] for f in finals], dtype=float)
    spin_vals = np.array([f["spin_length_at_min"] for f in finals], dtype=float)
    penalty_len = float(np.mean(np.maximum(0.0, 0.35 - spin_vals)) * config.get("objective", {}).get("lambda_len", 2.0))
    penalty_ctrl = 0.02 * abs(float(theta.get("gradient", 0.0))) + 0.02 * abs(float(theta.get("jz_final", model.get("jz", 0.35))) - float(model.get("jz", 0.35)))
    objective = float(np.mean(xi_vals) + penalty_len + penalty_ctrl)
    return {"theta": theta, "objective": objective, "finals": finals, "resources": resources, "mean_xi2": float(np.mean(xi_vals)), "mean_xi2_db": float(10*np.log10(max(np.mean(xi_vals),1e-300))), "mean_spin_length": float(np.mean(spin_vals))}

def baseline_theta(t_max: float) -> dict:
    return {"echo_time": None, "hold_time": float(t_max), "ramp_duration": 0.0, "jz_final": 0.35, "gradient": 0.0, "postselect_min_occ": None}
