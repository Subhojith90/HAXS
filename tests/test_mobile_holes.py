from haxs.lattice.graphs import hypercubic_lattice
from haxs.lattice.occupancy import sample_fixed_count
from haxs.models.mobile_holes import mobile_occupancy_trajectory


def test_mobile_hole_count_preserved():
    g=hypercubic_lattice((8,), False)
    occ=sample_fixed_count(g.n_sites,2,seed=5)
    traj=mobile_occupancy_trajectory(g, occ, 10, eta=1.0, dt=0.2, seed=6)
    assert all((~row).sum()==2 for row in traj)
