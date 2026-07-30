import numpy as np
from haxs.lattice.graphs import hypercubic_lattice
from haxs.lattice.occupancy import sample_bernoulli
from haxs.lattice.neighbours import active_bond_count

def test_static_vacancy_bond_scaling():
    g=hypercubic_lattice((5,5), False); ph=0.2
    vals=[active_bond_count(g,sample_bernoulli(g.n_sites,ph,s)) for s in range(80)]
    expected=len(g.bonds)*(1-ph)**2
    assert abs(np.mean(vals)-expected)/expected < 0.25
