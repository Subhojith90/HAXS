
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'src'))
from haxs.lattice.graphs import hypercubic_lattice
from haxs.methods.dtwa import run_dtwa

def test_explicit_occupancy_seed_holds_initial_occupancy_fixed_when_phase_changes():
    g=hypercubic_lattice((2,2), False)
    t=np.linspace(0,0.1,3)
    a=run_dtwa(g,t,hole_fraction=0.25,mobile_eta=0.5,lambda_sd=0.1,n_traj=4,seed=1,occupancy_seed=101,hole_path_seed=201,phase_batch_seed=301)
    b=run_dtwa(g,t,hole_fraction=0.25,mobile_eta=0.5,lambda_sd=0.1,n_traj=4,seed=2,occupancy_seed=101,hole_path_seed=201,phase_batch_seed=302)
    assert np.array_equal(a['initial_occupancy'], b['initial_occupancy'])
    assert np.array_equal(a['occupancy_trajectory'], b['occupancy_trajectory'])
    assert a['phase_batch_seed'] != b['phase_batch_seed']

def test_explicit_occupancy_seed_changes_occupancy_when_requested():
    g=hypercubic_lattice((3,3), False)
    t=np.linspace(0,0.1,3)
    a=run_dtwa(g,t,hole_fraction=0.33,mobile_eta=0.0,lambda_sd=0.0,n_traj=4,seed=1,occupancy_seed=101,hole_path_seed=0,phase_batch_seed=301)
    b=run_dtwa(g,t,hole_fraction=0.33,mobile_eta=0.0,lambda_sd=0.0,n_traj=4,seed=1,occupancy_seed=102,hole_path_seed=0,phase_batch_seed=301)
    assert not np.array_equal(a['initial_occupancy'], b['initial_occupancy'])
