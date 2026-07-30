from __future__ import annotations
from dataclasses import dataclass, asdict
import numpy as np

@dataclass(frozen=True)
class ResourceAccount:
    n_sites: int
    n_occ: float
    n_eff: float
    postselection_probability: float
    xi2_conditional: float
    xi2_unconditional: float
    spin_length: float
    metrological_gain_db_resource: float

    def as_dict(self) -> dict[str, float]:
        data = asdict(self)
        # Stable public aliases used in tables/tests.
        data["N_sites"] = data["n_sites"]
        data["N_occ"] = data["n_occ"]
        data["N_eff"] = data["n_eff"]
        data["metrological_gain_resource_penalized"] = data["metrological_gain_db_resource"]
        return data

def account_resources(n_sites: int, n_occ_values, xi2: float, spin_length: float, postselect_mask=None) -> ResourceAccount:
    occ = np.asarray(n_occ_values, dtype=float)
    if occ.size == 0:
        occ = np.array([0.0])
    if postselect_mask is None:
        mask = np.ones(occ.shape, dtype=bool)
    else:
        mask = np.asarray(postselect_mask, dtype=bool)
        if mask.size != occ.size:
            mask = np.ones(occ.shape, dtype=bool)
    p = float(np.mean(mask))
    n_eff = float(np.mean(occ[mask])) if np.any(mask) else 0.0
    xi2_cond = float(xi2)
    xi2_uncond = float(xi2 / max(p, 1e-12))
    gain = float(-10.0 * np.log10(max(xi2_uncond, 1e-300)))
    return ResourceAccount(int(n_sites), float(np.mean(occ)), n_eff, p, xi2_cond, xi2_uncond, float(spin_length), gain)

def postselection_mask(n_occ_values, min_occ: int | None = None) -> np.ndarray:
    occ = np.asarray(n_occ_values, dtype=float)
    if min_occ is None:
        return np.ones_like(occ, dtype=bool)
    return occ >= int(min_occ)
