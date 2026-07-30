from __future__ import annotations
import numpy as np

def local_cluster_sizes(graph, occupancy) -> dict[str, float]:
    occ = np.asarray(occupancy, dtype=bool)
    seen = set(); sizes = []
    for i, o in enumerate(occ):
        if not o or i in seen:
            continue
        stack = [i]; seen.add(i); size = 0
        while stack:
            cur = stack.pop(); size += 1
            for nb in graph.neighbors[cur]:
                if occ[nb] and nb not in seen:
                    seen.add(nb); stack.append(nb)
        sizes.append(size)
    return {"n_clusters": int(len(sizes)), "largest_cluster": int(max(sizes) if sizes else 0), "mean_cluster": float(np.mean(sizes) if sizes else 0.0)}

def cluster_weighted_bond_fraction(graph, occupancy) -> float:
    stats = local_cluster_sizes(graph, occupancy)
    return float(stats["largest_cluster"] / max(graph.n_sites, 1))
