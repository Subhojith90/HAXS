import numpy as np
from haxs.lattice.graphs import hypercubic_lattice
from haxs.lattice.occupancy import sample_fixed_count
from haxs.models.mobile_holes import random_walk_holes, occupancy_trajectory_from_holes, mobile_occupancy_trajectory
from haxs.models.spin_density import spin_density_field
from haxs.models.controls import ControlProtocol, apply_echo_x


def test_mobile_hole_engine_preserves_hole_count():
    g = hypercubic_lattice((8,), False)
    traj = random_walk_holes(g, [1, 5], n_steps=8, hop_probability=0.5, seed=10)
    occ = occupancy_trajectory_from_holes(g.n_sites, traj)
    assert np.all((~occ).sum(axis=1) == 2)


def test_zero_mobility_equals_static_limit():
    g = hypercubic_lattice((8,), False)
    occ = sample_fixed_count(g.n_sites, 2, seed=2)
    traj = mobile_occupancy_trajectory(g, occ, 4, eta=0.0, dt=0.1, seed=3)
    assert np.all(traj == occ)


def test_spin_density_field_zero_limits():
    g = hypercubic_lattice((4,), False)
    assert np.allclose(spin_density_field(g, np.ones(g.n_sites, dtype=bool), 0.5), 0.0)
    occ = sample_fixed_count(g.n_sites, 1, seed=1)
    assert np.allclose(spin_density_field(g, occ, 0.0), 0.0)


def test_echo_control_flips_yz_only():
    spins = np.array([[[0.5, 0.2, -0.1]]])
    out = apply_echo_x(spins)
    assert out[0,0,0] == spins[0,0,0]
    assert out[0,0,1] == -spins[0,0,1]
    assert out[0,0,2] == -spins[0,0,2]
    assert ControlProtocol(echo_times=(0.2,)).echo_crossed(0.1, 0.3)
