from __future__ import annotations
import numpy as np
from haxs.models.mobile_holes import mobile_occupancy_trajectory
from haxs.models.spin_density import spin_density_field, field_autocorrelation
from haxs.observables.diagnostics import hole_scrambling_number

def make_hole_trajectory(graph, initial_occupancy, times, eta: float, seed: int):
    times = np.asarray(times, dtype=float)
    dt = float(times[1] - times[0]) if len(times) > 1 else 0.0
    return mobile_occupancy_trajectory(graph, initial_occupancy, len(times), eta, dt, seed)

def trajectory_diagnostics(graph, occ_traj, lambda_sd: float, eta: float, hole_fraction: float, times) -> dict[str, float]:
    fields = np.array([spin_density_field(graph, occ, lambda_sd) for occ in occ_traj])
    ac = field_autocorrelation(fields.reshape(len(fields), -1))
    final_t = float(np.asarray(times)[-1]) if len(times) else 0.0
    return {
        "field_autocorr_lag1": float(ac[1]) if len(ac) > 1 else 1.0,
        "field_autocorr_final": float(ac[-1]) if len(ac) else 1.0,
        "hole_scrambling_number": hole_scrambling_number(hole_fraction, eta, lambda_sd, graph.coordination_average, final_t),
    }
