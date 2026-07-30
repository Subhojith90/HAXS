import numpy as np
from haxs.lattice.graphs import hypercubic_lattice
from haxs.lattice.occupancy import sample_bernoulli, sample_fixed_count
from haxs.lattice.neighbours import active_bond_count

def test_fixed_count():
    occ=sample_fixed_count(10,3,seed=1); assert occ.sum()==7

def test_bernoulli_expected_occupancy():
    vals=[sample_bernoulli(200,0.2,seed=s).mean() for s in range(20)]
    assert abs(np.mean(vals)-0.8)<0.05

def test_active_bond_count_bounds():
    g=hypercubic_lattice((4,4), False); occ=sample_fixed_count(g.n_sites,4,seed=3)
    assert 0 <= active_bond_count(g,occ) <= len(g.bonds)
