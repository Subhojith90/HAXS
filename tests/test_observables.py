import numpy as np
from haxs.observables.squeezing import css_reference, wineland_squeezing
from haxs.utils.math import xi2_to_db, db_to_xi2

def test_css_xi2_one():
    sq=css_reference(12); assert abs(sq['xi2']-1.0)<1e-12; assert abs(sq['xi2_db'])<1e-12

def test_db_conversion():
    assert abs(db_to_xi2(xi2_to_db(0.5))-0.5)<1e-12

def test_covariance_finite_symmetric():
    mean=np.array([4.0,0,0]); cov=np.diag([0,2,3]); sq=wineland_squeezing(mean,cov,8)
    assert np.isfinite(sq['xi2']); assert sq['min_var']==2
