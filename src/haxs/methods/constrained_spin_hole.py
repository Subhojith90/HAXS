from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations, product

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import expm_multiply

from haxs.lattice.graphs import LatticeGraph
from haxs.observables.squeezing import wineland_squeezing

HOLE = 0
DOWN = 1
UP = 2


@dataclass(frozen=True)
class ConstrainedBasis:
    states: tuple[tuple[int, ...], ...]
    index: dict[tuple[int, ...], int]
    n_sites: int
    n_holes: int

    @property
    def dimension(self) -> int:
        return len(self.states)

    @property
    def n_particles(self) -> int:
        return self.n_sites - self.n_holes


def build_basis(n_sites: int, n_holes: int) -> ConstrainedBasis:
    n_sites, n_holes = int(n_sites), int(n_holes)
    if not 0 <= n_holes < n_sites:
        raise ValueError("constrained basis requires 0 <= n_holes < n_sites")
    states: list[tuple[int, ...]] = []
    for holes in combinations(range(n_sites), n_holes):
        hole_set = set(holes)
        occupied = [site for site in range(n_sites) if site not in hole_set]
        for spins in product((DOWN, UP), repeat=len(occupied)):
            state = [HOLE] * n_sites
            for site, spin in zip(occupied, spins):
                state[site] = spin
            states.append(tuple(state))
    frozen = tuple(states)
    return ConstrainedBasis(frozen, {state: i for i, state in enumerate(frozen)}, n_sites, n_holes)


def _sz(local_state: int) -> float:
    if local_state == UP:
        return 0.5
    if local_state == DOWN:
        return -0.5
    return 0.0


def build_constrained_hamiltonian(
    graph: LatticeGraph,
    basis: ConstrainedBasis,
    j_perp: float = 1.0,
    jz: float = 0.35,
    hopping_t: float = 0.0,
    lambda_sd: float = 0.0,
) -> sparse.csr_matrix:
    """Hard-core spin-carrier Hamiltonian with spin-preserving hopping.

    Local states are hole/down/up. Hopping exchanges a hole with a neighboring
    spin and therefore transports that spin. The carrier convention is hard-core
    bosonic; no fermionic Jordan-Wigner sign is inserted.
    """
    rows: list[int] = []
    cols: list[int] = []
    values: list[complex] = []
    for row, state in enumerate(basis.states):
        diagonal = 0.0
        holes = np.asarray([value == HOLE for value in state], dtype=bool)
        for a_raw, b_raw in graph.bonds:
            a, b = int(a_raw), int(b_raw)
            sa, sb = state[a], state[b]
            if sa != HOLE and sb != HOLE:
                diagonal += float(jz) * _sz(sa) * _sz(sb)
                if sa != sb:
                    flipped = list(state)
                    flipped[a], flipped[b] = flipped[b], flipped[a]
                    rows.append(row); cols.append(basis.index[tuple(flipped)]); values.append(0.5 * float(j_perp))
            elif float(hopping_t) != 0.0 and ((sa == HOLE) ^ (sb == HOLE)):
                hopped = list(state)
                hopped[a], hopped[b] = hopped[b], hopped[a]
                rows.append(row); cols.append(basis.index[tuple(hopped)]); values.append(-float(hopping_t))
        if float(lambda_sd) != 0.0:
            for site, local in enumerate(state):
                if local != HOLE:
                    neighboring_holes = sum(bool(holes[neighbor]) for neighbor in graph.neighbors[site])
                    diagonal += float(lambda_sd) * neighboring_holes * _sz(local)
        rows.append(row); cols.append(row); values.append(diagonal)
    matrix = sparse.coo_matrix((values, (rows, cols)), shape=(basis.dimension, basis.dimension), dtype=complex).tocsr()
    return 0.5 * (matrix + matrix.getH())


def initial_css_x_with_holes(basis: ConstrainedBasis, holes: list[int] | tuple[int, ...]) -> np.ndarray:
    hole_set = {int(site) for site in holes}
    if len(hole_set) != basis.n_holes:
        raise ValueError("initial hole list does not match basis hole sector")
    amplitude = 1.0 / np.sqrt(2**basis.n_particles)
    state = np.zeros(basis.dimension, dtype=complex)
    for index, local in enumerate(basis.states):
        if {site for site, value in enumerate(local) if value == HOLE} == hole_set:
            state[index] = amplitude
    norm = np.linalg.norm(state)
    if norm <= 0:
        raise ValueError("initial hole configuration is absent from basis")
    return state / norm


def collective_operators(basis: ConstrainedBasis) -> tuple[sparse.csr_matrix, sparse.csr_matrix, sparse.csr_matrix]:
    plus_rows: list[int] = []
    plus_cols: list[int] = []
    for col, state in enumerate(basis.states):
        for site, local in enumerate(state):
            if local == DOWN:
                raised = list(state); raised[site] = UP
                plus_rows.append(basis.index[tuple(raised)]); plus_cols.append(col)
    s_plus = sparse.coo_matrix((np.ones(len(plus_rows), dtype=complex), (plus_rows, plus_cols)), shape=(basis.dimension, basis.dimension)).tocsr()
    s_minus = s_plus.getH().tocsr()
    sx = 0.5 * (s_plus + s_minus)
    sy = (s_plus - s_minus) / (2j)
    sz_diag = np.asarray([sum(_sz(value) for value in state) for state in basis.states], dtype=float)
    sz = sparse.diags(sz_diag, format="csr", dtype=complex)
    return sx.tocsr(), sy.tocsr(), sz


def _state_observables(psi: np.ndarray, operators) -> dict[str, float]:
    means = np.asarray([np.vdot(psi, operator @ psi).real for operator in operators], dtype=float)
    covariance = np.zeros((3, 3), dtype=float)
    for a in range(3):
        for b in range(3):
            sym = 0.5 * (operators[a] @ operators[b] + operators[b] @ operators[a])
            covariance[a, b] = float(np.vdot(psi, sym @ psi).real - means[a] * means[b])
    return {"means": means, "covariance": 0.5 * (covariance + covariance.T)}


def hole_density(psi: np.ndarray, basis: ConstrainedBasis) -> np.ndarray:
    probabilities = np.abs(psi) ** 2
    density = np.zeros(basis.n_sites, dtype=float)
    for probability, state in zip(probabilities, basis.states):
        density += probability * np.asarray([value == HOLE for value in state], dtype=float)
    return density


def hole_configuration_probabilities(psi: np.ndarray, basis: ConstrainedBasis) -> dict[tuple[int, ...], float]:
    output: dict[tuple[int, ...], float] = {}
    for probability, state in zip(np.abs(psi) ** 2, basis.states):
        holes = tuple(site for site, value in enumerate(state) if value == HOLE)
        output[holes] = output.get(holes, 0.0) + float(probability)
    return output


def run_constrained_curve(
    graph: LatticeGraph,
    times: np.ndarray,
    initial_holes: list[int] | tuple[int, ...],
    j_perp: float = 1.0,
    jz: float = 0.35,
    hopping_t: float = 0.0,
    lambda_sd: float = 0.0,
) -> dict[str, object]:
    times = np.asarray(times, dtype=float)
    basis = build_basis(graph.n_sites, len(initial_holes))
    hamiltonian = build_constrained_hamiltonian(graph, basis, j_perp, jz, hopping_t, lambda_sd)
    initial = initial_css_x_with_holes(basis, initial_holes)
    states = expm_multiply((-1j) * hamiltonian, initial, start=float(times[0]), stop=float(times[-1]), num=len(times), endpoint=True)
    operators = collective_operators(basis)
    rows, densities, histories = [], [], []
    for time_value, psi in zip(times, states):
        observed = _state_observables(psi, operators)
        squeezing = wineland_squeezing(observed["means"], observed["covariance"], basis.n_particles)
        norm_error = abs(float(np.vdot(psi, psi).real) - 1.0)
        density = hole_density(psi, basis)
        probabilities = hole_configuration_probabilities(psi, basis)
        rows.append([float(time_value), *observed["means"], squeezing["xi2"], squeezing["xi2_db"], squeezing["min_var"], 2 * squeezing["spin_norm"] / basis.n_particles, float(basis.n_particles), norm_error, float(density.sum())])
        densities.append(density)
        histories.append(probabilities)
    return {
        "columns": np.asarray(["time", "Sx", "Sy", "Sz", "xi2", "xi2_db", "min_var", "spin_length", "particle_number", "norm_error", "hole_number_expectation"]),
        "data": np.asarray(rows, dtype=float),
        "hole_density": np.asarray(densities, dtype=float),
        "hole_configuration_probabilities": histories,
        "basis_dimension": basis.dimension,
        "n_particles": basis.n_particles,
        "n_holes": basis.n_holes,
        "hamiltonian_hermiticity_error": float(sparse.linalg.norm(hamiltonian - hamiltonian.getH())),
    }

