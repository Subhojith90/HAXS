import numpy as np
from haxs.methods.ed import two_spin_error, run_ed_curve
from haxs.lattice.graphs import hypercubic_lattice

def test_two_spin_analytic():
    assert two_spin_error(np.linspace(0,1,5)) < 1e-10

def test_ed_curve_columns():
    g=hypercubic_lattice((2,), False); res=run_ed_curve(g, np.linspace(0,0.2,3))
    assert res['data'].shape[0]==3; assert 'xi2' in list(res['columns'])
