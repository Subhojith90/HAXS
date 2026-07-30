from __future__ import annotations
from dataclasses import dataclass
import numpy as np

@dataclass(frozen=True)
class LatticeGraph:
    shape: tuple[int, ...]
    periodic: bool
    coords: np.ndarray
    bonds: np.ndarray
    neighbors: tuple[tuple[int, ...], ...]

    @property
    def n_sites(self) -> int:
        return int(np.prod(self.shape))

    @property
    def dim(self) -> int:
        return len(self.shape)

    @property
    def coordination_average(self) -> float:
        return float(np.mean([len(n) for n in self.neighbors])) if self.n_sites else 0.0

def hypercubic_lattice(shape: tuple[int, ...] | list[int], periodic: bool = False) -> LatticeGraph:
    shape = tuple(int(x) for x in shape)
    coords = np.array(list(np.ndindex(shape)), dtype=int)
    index = {tuple(c): i for i, c in enumerate(coords)}
    bonds: list[tuple[int, int]] = []
    neigh: list[set[int]] = [set() for _ in range(len(coords))]
    for i, c in enumerate(coords):
        for ax, L in enumerate(shape):
            c2 = c.copy()
            c2[ax] += 1
            if c2[ax] >= L:
                if periodic:
                    c2[ax] = 0
                else:
                    continue
            j = index[tuple(c2)]
            if i != j:
                a, b = sorted((i, j))
                if (a, b) not in bonds:
                    bonds.append((a, b))
                    neigh[a].add(b); neigh[b].add(a)
    bonds_arr = np.array(sorted(bonds), dtype=int).reshape((-1, 2)) if bonds else np.zeros((0, 2), dtype=int)
    neighbors = tuple(tuple(sorted(s)) for s in neigh)
    return LatticeGraph(shape=shape, periodic=bool(periodic), coords=coords, bonds=bonds_arr, neighbors=neighbors)

def chain(L: int, periodic: bool = False) -> LatticeGraph:
    return hypercubic_lattice((int(L),), periodic)

def square(Lx: int, Ly: int, periodic: bool = False) -> LatticeGraph:
    return hypercubic_lattice((int(Lx), int(Ly)), periodic)

def cubic(Lx: int, Ly: int, Lz: int, periodic: bool = False) -> LatticeGraph:
    return hypercubic_lattice((int(Lx), int(Ly), int(Lz)), periodic)

def coordination_numbers(graph: LatticeGraph) -> np.ndarray:
    return np.array([len(n) for n in graph.neighbors], dtype=int)
