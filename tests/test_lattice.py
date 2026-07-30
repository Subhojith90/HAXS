from haxs.lattice.graphs import hypercubic_lattice, coordination_numbers

def test_lattice_neighbor_counts_open():
    g1=hypercubic_lattice((5,), False); assert len(g1.bonds)==4; assert coordination_numbers(g1).tolist()==[1,2,2,2,1]
    g2=hypercubic_lattice((3,3), False); assert len(g2.bonds)==12; assert max(coordination_numbers(g2))==4
    g3=hypercubic_lattice((2,2,2), False); assert len(g3.bonds)==12; assert min(coordination_numbers(g3))==3

def test_lattice_periodic_chain():
    g=hypercubic_lattice((5,), True); assert len(g.bonds)==5; assert all(len(n)==2 for n in g.neighbors)
