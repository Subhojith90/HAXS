import numpy as np
from haxs.lattice.graphs import chain, square, cubic, hypercubic_lattice
from haxs.lattice.occupancy import sample_bernoulli, sample_fixed_count
from haxs.lattice.neighbours import active_bond_count, disrupted_bond_fraction


def test_lattice_neighbour_counts_open_boundaries():
    assert len(chain(5).bonds) == 4
    assert len(square(3, 3).bonds) == 12
    assert len(cubic(2, 2, 2).bonds) == 12


def test_static_vacancy_sampler_count_and_bounds():
    occ = sample_fixed_count(20, 5, seed=1)
    assert int((~occ).sum()) == 5
    g = hypercubic_lattice((20,), False)
    frac = disrupted_bond_fraction(g, occ)
    assert 0.0 <= frac <= 1.0


def test_bernoulli_expected_occupancy_is_reasonable():
    vals = [sample_bernoulli(200, 0.2, seed=i).mean() for i in range(20)]
    assert abs(np.mean(vals) - 0.8) < 0.05
