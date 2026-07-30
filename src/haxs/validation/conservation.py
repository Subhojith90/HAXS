from __future__ import annotations
import numpy as np
from haxs.lattice.graphs import hypercubic_lattice
from haxs.methods.ed import build_xxz_hamiltonian, initial_css_x, evolve_state, total_sz_operator

def sz_conservation_check(n: int = 4, jz: float = 0.35) -> dict[str, float | bool]:
    graph = hypercubic_lattice((n,), False)
    H = build_xxz_hamiltonian(graph, 1.0, jz)
    times = np.linspace(0.0, 1.0, 6)
    states = evolve_state(H, initial_css_x(n), times)
    Sz = total_sz_operator(n)
    vals = np.array([np.vdot(psi, Sz @ psi).real for psi in states])
    drift = float(np.max(np.abs(vals - vals[0])))
    return {"sz_max_drift": drift, "passed": bool(drift < 1e-10)}
