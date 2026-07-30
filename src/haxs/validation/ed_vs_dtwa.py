from __future__ import annotations
import numpy as np
from haxs.lattice.graphs import hypercubic_lattice
from haxs.methods.ed import run_ed_curve
from haxs.methods.dtwa import run_dtwa

def compare_ed_dtwa_short_time(seed: int = 1729) -> dict[str, float | bool]:
    graph = hypercubic_lattice((4,), False)
    times = np.linspace(0.0, 0.4, 9)
    ed = run_ed_curve(graph, times, jz=0.35)["data"]
    dt = run_dtwa(graph, times, jz=0.35, n_traj=512, seed=seed)["data"]
    diff = float(np.sqrt(np.mean((ed[:,4] - dt[:,4])**2)))
    return {"ed_dtwa_xi2_rmse_short_time": diff, "passed": bool(diff < 0.85)}
