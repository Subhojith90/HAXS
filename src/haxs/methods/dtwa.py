from __future__ import annotations
import numpy as np
from haxs.lattice.graphs import LatticeGraph
from haxs.lattice.occupancy import sample_bernoulli, sample_fixed_count
from haxs.lattice.neighbours import active_bond_count
from haxs.models.controls import ControlProtocol, apply_echo_x
from haxs.models.mobile_holes import mobile_occupancy_trajectory
from haxs.models.spin_density import spin_density_field, hole_spin_covariance
from haxs.observables.collective_spin import mean_and_covariance, spin_length
from haxs.observables.squeezing import wineland_squeezing
from haxs.utils.rng import rng


def sample_css_x(n_traj: int, n_sites: int, seed: int) -> np.ndarray:
    gen = rng(seed)
    spins = np.zeros((int(n_traj), int(n_sites), 3), dtype=float)
    spins[..., 0] = 0.5
    spins[..., 1] = 0.5 * gen.choice([-1.0, 1.0], size=(int(n_traj), int(n_sites)))
    spins[..., 2] = 0.5 * gen.choice([-1.0, 1.0], size=(int(n_traj), int(n_sites)))
    return spins

def _field_from_bonds(spins: np.ndarray, graph: LatticeGraph, occupancy: np.ndarray, j_perp: float, jz: float) -> np.ndarray:
    B = np.zeros_like(spins)
    occ = np.asarray(occupancy, dtype=bool)
    for i, j in graph.bonds:
        if not (occ[i] and occ[j]):
            continue
        sj = spins[:, j, :]
        si = spins[:, i, :]
        B[:, i, 0] += j_perp * sj[:, 0]
        B[:, i, 1] += j_perp * sj[:, 1]
        B[:, i, 2] += jz * sj[:, 2]
        B[:, j, 0] += j_perp * si[:, 0]
        B[:, j, 1] += j_perp * si[:, 1]
        B[:, j, 2] += jz * si[:, 2]
    return B

def _rhs(spins: np.ndarray, graph: LatticeGraph, occupancy: np.ndarray, j_perp: float, jz: float, fields_z: np.ndarray) -> np.ndarray:
    B = _field_from_bonds(spins, graph, occupancy, j_perp, jz)
    B[..., 2] += fields_z[None, :]
    return np.cross(B, spins, axis=-1)

def _renormalize_to_previous_lengths(out: np.ndarray, reference: np.ndarray) -> np.ndarray:
    """Preserve the DTWA phase-point norm used at initialization.

    The CSS-x discrete phase-point sampler uses (Sx,Sy,Sz)=(1/2, ±1/2, ±1/2).
    These are DTWA phase-space samples, not classical spin vectors of length 1/2.
    The equations of motion are precessional and should preserve each sampled vector
    length up to numerical integration error.  The previous implementation forced every
    vector to length 1/2 after the first RK4 step, producing the supervisory-audit
    artifact: a normalized collective spin-length collapse from approximately 1 to
    1/sqrt(3).  This repair keeps each trajectory/site vector on its own initial
    phase-point shell instead.
    """
    target = np.linalg.norm(reference, axis=-1, keepdims=True)
    current = np.linalg.norm(out, axis=-1, keepdims=True)
    scale = np.ones_like(current)
    mask = current > 1e-14
    scale[mask] = target[mask] / current[mask]
    return out * scale

def _rk4_step(spins: np.ndarray, graph: LatticeGraph, occupancy: np.ndarray, dt: float, j_perp: float, jz: float, fields_z: np.ndarray) -> np.ndarray:
    k1 = _rhs(spins, graph, occupancy, j_perp, jz, fields_z)
    k2 = _rhs(spins + 0.5 * dt * k1, graph, occupancy, j_perp, jz, fields_z)
    k3 = _rhs(spins + 0.5 * dt * k2, graph, occupancy, j_perp, jz, fields_z)
    k4 = _rhs(spins + dt * k3, graph, occupancy, j_perp, jz, fields_z)
    out = spins + (dt / 6.0) * (k1 + 2*k2 + 2*k3 + k4)
    return _renormalize_to_previous_lengths(out, spins)

def collective_samples(spins: np.ndarray, occupancy: np.ndarray) -> np.ndarray:
    occ = np.asarray(occupancy, dtype=float)
    return np.sum(spins * occ[None, :, None], axis=1)

def observables_from_spins(spins: np.ndarray, occupancy: np.ndarray, graph: LatticeGraph) -> dict[str, float]:
    samples = collective_samples(spins, occupancy)
    mean, cov = mean_and_covariance(samples)
    n_eff = int(np.sum(occupancy))
    sq = wineland_squeezing(mean, cov, n_eff)
    avg_sz = np.mean(spins[..., 2], axis=0)
    return {
        "Sx": float(mean[0]), "Sy": float(mean[1]), "Sz": float(mean[2]),
        "xi2": float(sq["xi2"]), "xi2_db": float(sq["xi2_db"]), "min_var": float(sq["min_var"]),
        "spin_length": spin_length(mean, n_eff), "N_eff": float(n_eff),
        "active_bonds": float(active_bond_count(graph, occupancy)),
        "hole_spin_covariance": hole_spin_covariance(occupancy, avg_sz),
    }

def run_dtwa(
    graph: LatticeGraph,
    times: np.ndarray,
    j_perp: float = 1.0,
    jz: float = 0.35,
    hole_fraction: float = 0.0,
    mobile_eta: float = 0.0,
    lambda_sd: float = 0.0,
    n_traj: int = 64,
    seed: int = 1729,
    control: ControlProtocol | None = None,
    fixed_hole_count: int | None = None,
    store_trajectories: bool = False,
    occupancy_seed: int | None = None,
    hole_path_seed: int | None = None,
    phase_batch_seed: int | None = None,
    initial_occupancy: np.ndarray | None = None,
    initial_spins: np.ndarray | None = None,
    integration_substeps: int = 1,
    return_component_statistics: bool = False,
) -> dict[str, object]:
    times = np.asarray(times, dtype=float)
    if len(times) < 1:
        raise ValueError("times must contain at least one value")
    occ_seed = int(seed + 17 if occupancy_seed is None else occupancy_seed)
    path_seed = int(seed + 29 if hole_path_seed is None else hole_path_seed)
    phase_seed = int(seed + 43 if phase_batch_seed is None else phase_batch_seed)
    n_holes = int(round(hole_fraction * graph.n_sites)) if fixed_hole_count is None else int(fixed_hole_count)
    if initial_occupancy is not None:
        initial_occ = np.asarray(initial_occupancy, dtype=bool).copy()
        if initial_occ.shape != (graph.n_sites,):
            raise ValueError(f"initial_occupancy must have shape ({graph.n_sites},)")
        n_holes = int(graph.n_sites - initial_occ.sum())
        if fixed_hole_count is not None and n_holes != int(fixed_hole_count):
            raise ValueError("initial_occupancy and fixed_hole_count disagree")
    else:
        initial_occ = sample_fixed_count(graph.n_sites, n_holes, occ_seed) if fixed_hole_count is not None else sample_bernoulli(graph.n_sites, hole_fraction, occ_seed)
    if np.sum(initial_occ) <= 1:
        initial_occ = np.ones(graph.n_sites, dtype=bool)
    substeps = int(integration_substeps)
    if substeps < 1:
        raise ValueError("integration_substeps must be a positive integer")
    dt = float(times[1] - times[0]) if len(times) > 1 else 0.0
    occ_traj = mobile_occupancy_trajectory(graph, initial_occ, len(times), mobile_eta, dt, path_seed)
    if initial_spins is None:
        spins = sample_css_x(n_traj, graph.n_sites, phase_seed)
    else:
        spins = np.asarray(initial_spins, dtype=float).copy()
        if spins.ndim != 3 or spins.shape[1:] != (graph.n_sites, 3):
            raise ValueError(f"initial_spins must have shape (n_traj, {graph.n_sites}, 3)")
        if len(spins) < 2 or not np.isfinite(spins).all():
            raise ValueError("initial_spins must contain at least two finite phase points")
        n_traj = int(len(spins))
    rows = []
    snapshots = []
    component_statistics = []
    ctrl = control or ControlProtocol(enabled=False, jz_initial=jz, final_time=float(times[-1]))
    for k, t in enumerate(times):
        occ = occ_traj[k]
        obs = observables_from_spins(spins, occ, graph)
        rows.append([float(t), obs["Sx"], obs["Sy"], obs["Sz"], obs["xi2"], obs["xi2_db"], obs["min_var"], obs["spin_length"], obs["N_eff"], obs["active_bonds"], obs["hole_spin_covariance"]])
        if return_component_statistics:
            samples = collective_samples(spins, occ)
            standard_errors = np.std(samples, axis=0, ddof=1) / np.sqrt(float(len(samples)))
            component_statistics.append({
                "time": float(t),
                "n": int(len(samples)),
                "Sx_mean": float(obs["Sx"]),
                "Sy_mean": float(obs["Sy"]),
                "Sz_mean": float(obs["Sz"]),
                "Sx_se": float(standard_errors[0]),
                "Sy_se": float(standard_errors[1]),
                "Sz_se": float(standard_errors[2]),
            })
        if store_trajectories:
            snapshots.append(spins.copy())
        if k == len(times) - 1:
            break
        t0, t1 = float(times[k]), float(times[k+1])
        step_dt = (t1 - t0) / float(substeps)
        for substep in range(substeps):
            sub_t0 = t0 + substep * step_dt
            sub_t1 = sub_t0 + step_dt
            sub_jz = ctrl.jz_at(sub_t0) if ctrl.enabled else jz
            sub_fields = np.zeros(graph.n_sites, dtype=float)
            if ctrl.enabled:
                sub_fields += ctrl.fields_at(graph, sub_t0)
            if lambda_sd != 0.0:
                sub_fields += spin_density_field(graph, occ, lambda_sd)
            spins = _rk4_step(spins, graph, occ, step_dt, j_perp, sub_jz, sub_fields)
            if ctrl.enabled and ctrl.echo_crossed(sub_t0, sub_t1):
                spins = apply_echo_x(spins)
    cols = ["time","Sx","Sy","Sz","xi2","xi2_db","min_var","spin_length","N_eff","active_bonds","hole_spin_covariance"]
    data = np.array(rows, dtype=float)
    return {
        "columns": np.array(cols),
        "data": data,
        "initial_occupancy": initial_occ.astype(int),
        "occupancy_trajectory": occ_traj.astype(int),
        "stored_trajectories": snapshots,
        "component_statistics": component_statistics,
        "occupancy_seed": occ_seed,
        "hole_path_seed": path_seed,
        "phase_batch_seed": phase_seed,
        "integration_substeps": substeps,
        "deterministic_initial_spins": initial_spins is not None,
    }

def curve_to_records(result: dict[str, object], label: str, seed: int) -> list[dict[str, float | str | int]]:
    cols = [str(c) for c in result["columns"]]
    out = []
    for row in np.asarray(result["data"]):
        d = {cols[i]: float(row[i]) for i in range(len(cols))}
        d["label"] = label; d["seed"] = int(seed)
        out.append(d)
    return out
