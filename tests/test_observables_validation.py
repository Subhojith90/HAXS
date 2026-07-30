import numpy as np
from haxs.validation.analytic_cases import validate_two_spin, validate_css
from haxs.validation.conservation import sz_conservation_check
from haxs.observables.collective_spin import mean_and_covariance
from haxs.observables.squeezing import wineland_squeezing
from haxs.utils.math import xi2_to_db, db_to_xi2


def test_two_spin_ed_matches_analytic():
    assert validate_two_spin()['passed']


def test_css_squeezing_is_one_at_t0():
    assert validate_css(6)['passed']


def test_db_conversion_roundtrip():
    x = 0.5
    assert abs(db_to_xi2(xi2_to_db(x)) - x) < 1e-12


def test_covariance_symmetric_and_finite():
    samples = np.array([[1.0,0,0], [0.9,0.1,0], [1.1,-0.1,0]])
    mean, cov = mean_and_covariance(samples)
    sq = wineland_squeezing(mean, cov, n_eff=6)
    assert np.allclose(cov, cov.T)
    assert np.isfinite(sq['xi2'])


def test_sz_conservation_holds():
    assert sz_conservation_check(4)['passed']
