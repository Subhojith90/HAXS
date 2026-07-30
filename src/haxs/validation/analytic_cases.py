from __future__ import annotations
import numpy as np
from haxs.methods.ed import two_spin_error
from haxs.observables.squeezing import css_reference

def validate_two_spin(j_perp: float = 1.0, jz: float = 0.35) -> dict[str, float | bool]:
    times = np.linspace(0.0, 1.7, 9)
    err = two_spin_error(times, j_perp, jz)
    return {"two_spin_max_state_error": float(err), "passed": bool(err < 1e-10)}

def validate_css(n_eff: int = 8) -> dict[str, float | bool]:
    sq = css_reference(n_eff)
    return {"css_xi2": float(sq["xi2"]), "css_xi2_db": float(sq["xi2_db"]), "passed": bool(abs(sq["xi2"] - 1.0) < 1e-12)}
