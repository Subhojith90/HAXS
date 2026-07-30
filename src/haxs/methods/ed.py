from __future__ import annotations
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import expm_multiply
from haxs.lattice.graphs import LatticeGraph, hypercubic_lattice
from haxs.observables.squeezing import wineland_squeezing

SX = 0.5 * np.array([[0, 1], [1, 0]], dtype=complex)
SY = 0.5 * np.array([[0, -1j], [1j, 0]], dtype=complex)
SZ = 0.5 * np.array([[1, 0], [0, -1]], dtype=complex)
ID2 = np.eye(2, dtype=complex)

def kron_all(ops: list[np.ndarray]) -> sparse.csr_matrix:
    out = sparse.csr_matrix([[1.0 + 0j]])
    for op in ops:
        out = sparse.kron(out, sparse.csr_matrix(op), format="csr")
    return out

def site_operator(n: int, site: int, op: np.ndarray) -> sparse.csr_matrix:
    return kron_all([op if i == site else ID2 for i in range(n)])

def two_site_operator(n: int, i: int, j: int, opi: np.ndarray, opj: np.ndarray) -> sparse.csr_matrix:
    return kron_all([opi if k == i else opj if k == j else ID2 for k in range(n)])

def build_xxz_hamiltonian(graph: LatticeGraph, j_perp: float = 1.0, jz: float = 0.35, fields: np.ndarray | None = None, occupancy: np.ndarray | None = None) -> sparse.csr_matrix:
    occ = np.ones(graph.n_sites, dtype=bool) if occupancy is None else np.asarray(occupancy, dtype=bool)
    active_sites = [i for i, o in enumerate(occ) if o]
    mapping = {old: new for new, old in enumerate(active_sites)}
    n = len(active_sites)
    dim = 2 ** n
    H = sparse.csr_matrix((dim, dim), dtype=complex)
    for a, b in graph.bonds:
        if occ[a] and occ[b]:
            i, j = mapping[int(a)], mapping[int(b)]
            H += j_perp * (two_site_operator(n, i, j, SX, SX) + two_site_operator(n, i, j, SY, SY))
            H += jz * two_site_operator(n, i, j, SZ, SZ)
    if fields is not None:
        f = np.asarray(fields, dtype=float)
        for old in active_sites:
            if abs(f[old]) > 0:
                H += f[old] * site_operator(n, mapping[old], SZ)
    return H.tocsr()

def initial_css_x(n: int) -> np.ndarray:
    plus = np.array([1.0, 1.0], dtype=complex) / np.sqrt(2.0)
    psi = plus
    for _ in range(n - 1):
        psi = np.kron(psi, plus)
    return psi.astype(complex)

def evolve_state(H: sparse.csr_matrix, psi0: np.ndarray, times: np.ndarray) -> np.ndarray:
    return expm_multiply((-1j) * H, psi0, start=float(times[0]), stop=float(times[-1]), num=len(times), endpoint=True)

def collective_ops(n: int) -> tuple[sparse.csr_matrix, sparse.csr_matrix, sparse.csr_matrix]:
    ops = []
    for op in (SX, SY, SZ):
        tot = sparse.csr_matrix((2**n, 2**n), dtype=complex)
        for i in range(n):
            tot += site_operator(n, i, op)
        ops.append(tot.tocsr())
    return tuple(ops)

def state_observables(psi: np.ndarray, ops: tuple[sparse.csr_matrix, sparse.csr_matrix, sparse.csr_matrix]) -> dict[str, object]:
    means = np.array([np.vdot(psi, op @ psi).real for op in ops])
    cov = np.zeros((3, 3), dtype=float)
    for a in range(3):
        for b in range(3):
            sym = 0.5 * (ops[a] @ ops[b] + ops[b] @ ops[a])
            cov[a, b] = (np.vdot(psi, sym @ psi).real - means[a] * means[b])
    return {"mean": means, "covariance": 0.5 * (cov + cov.T)}

def run_ed_curve(graph: LatticeGraph, times: np.ndarray, j_perp: float = 1.0, jz: float = 0.35, occupancy: np.ndarray | None = None) -> dict[str, np.ndarray]:
    occ = np.ones(graph.n_sites, dtype=bool) if occupancy is None else np.asarray(occupancy, dtype=bool)
    n = int(np.sum(occ))
    if n == 0:
        raise ValueError("ED requires at least one occupied site")
    H = build_xxz_hamiltonian(graph, j_perp, jz, occupancy=occ)
    psi0 = initial_css_x(n)
    states = evolve_state(H, psi0, np.asarray(times, dtype=float))
    ops = collective_ops(n)
    rows = []
    for t, psi in zip(times, states):
        obs = state_observables(psi, ops)
        sq = wineland_squeezing(obs["mean"], obs["covariance"], n)
        rows.append([float(t), *obs["mean"], sq["xi2"], sq["xi2_db"], sq["min_var"], 2*sq["spin_norm"]/n])
    arr = np.array(rows, dtype=float)
    return {"columns": np.array(["time","Sx","Sy","Sz","xi2","xi2_db","min_var","spin_length"]), "data": arr}

def two_spin_xxz_analytic_state(t: float, j_perp: float = 1.0, jz: float = 0.35) -> np.ndarray:
    phase_ud = np.exp(1j * jz * t / 4.0) * np.exp(-1j * j_perp * t / 2.0)
    phase_par = np.exp(-1j * jz * t / 4.0)
    return 0.5 * np.array([phase_par, phase_ud, phase_ud, phase_par], dtype=complex)

def two_spin_error(times: np.ndarray, j_perp: float = 1.0, jz: float = 0.35) -> float:
    graph = hypercubic_lattice((2,), periodic=False)
    H = build_xxz_hamiltonian(graph, j_perp, jz)
    states = evolve_state(H, initial_css_x(2), times)
    errs = [np.linalg.norm(states[k] - two_spin_xxz_analytic_state(float(t), j_perp, jz)) for k, t in enumerate(times)]
    return float(np.max(errs))

def total_sz_operator(n: int) -> sparse.csr_matrix:
    tot = sparse.csr_matrix((2**n, 2**n), dtype=complex)
    for i in range(n):
        tot += site_operator(n, i, SZ)
    return tot
