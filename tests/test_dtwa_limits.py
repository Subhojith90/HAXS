import numpy as np
from haxs.lattice.graphs import hypercubic_lattice
from haxs.methods.dtwa import run_dtwa
from haxs.models.mobile_holes import mobile_occupancy_trajectory
from haxs.lattice.occupancy import sample_fixed_count
from haxs.models.spin_density import spin_density_field

def test_mobile_zero_static_limit():
    g=hypercubic_lattice((6,), False); occ=sample_fixed_count(g.n_sites,2,1)
    traj=mobile_occupancy_trajectory(g,occ,5,eta=0.0,dt=0.1,seed=2)
    assert (traj == occ).all()

def test_spin_density_zero_holes():
    g=hypercubic_lattice((6,), False); field=spin_density_field(g,np.ones(g.n_sites,dtype=bool),0.5)
    assert np.allclose(field,0)

def test_zero_lambda_removes_sd_coupling():
    g=hypercubic_lattice((8,), False); times=np.linspace(0,0.3,5)
    a=run_dtwa(g,times,hole_fraction=0.2,lambda_sd=0,n_traj=32,seed=1)['data']
    b=run_dtwa(g,times,hole_fraction=0.2,lambda_sd=0,n_traj=32,seed=1)['data']
    assert np.allclose(a,b)
