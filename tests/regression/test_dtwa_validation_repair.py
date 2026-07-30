import math
import numpy as np
from haxs.lattice.graphs import hypercubic_lattice
from haxs.methods.dtwa import sample_css_x, run_dtwa


def test_css_phase_point_shell_is_not_forced_to_half():
    spins = sample_css_x(128, 6, seed=123)
    norms = np.linalg.norm(spins, axis=-1)
    assert np.allclose(norms, math.sqrt(3.0) / 2.0)
    collective = spins.sum(axis=1)
    sx_per_site = collective[:, 0].mean() / 6
    assert abs(sx_per_site - 0.5) < 1e-12


def test_no_first_step_spin_length_collapse_no_holes():
    g = hypercubic_lattice((4,), False)
    times = np.array([0.0, 0.05, 0.10])
    res = run_dtwa(g, times, hole_fraction=0.0, n_traj=512, seed=7)
    cols = list(res['columns'])
    spin_len = res['data'][:, cols.index('spin_length')]
    assert spin_len[0] > 0.95
    assert spin_len[1] > 0.90
    assert abs(spin_len[1] - spin_len[0]) < 0.10
    assert not np.isclose(spin_len[1], 1.0 / math.sqrt(3.0), atol=0.04)


def test_css_squeezing_near_zero_db_at_t0():
    g = hypercubic_lattice((8,), False)
    res = run_dtwa(g, np.array([0.0]), hole_fraction=0.0, n_traj=4096, seed=9)
    cols = list(res['columns'])
    xi2_db_t0 = res['data'][0, cols.index('xi2_db')]
    assert abs(xi2_db_t0) < 0.45
