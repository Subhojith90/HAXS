from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from haxs.lattice.graphs import LatticeGraph
from haxs.models.xxz import gradient_fields

CONTROL_CLASSIFICATION = {
    "global_rotation": "MVP plausible",
    "echo": "MVP plausible",
    "piecewise_jz": "MVP plausible",
    "linear_ramp": "MVP plausible",
    "global_gradient": "plausible but needs experimental check",
    "postselection": "MVP plausible with resource accounting",
    "local_feedback": "disabled",
}

@dataclass(frozen=True)
class ControlProtocol:
    enabled: bool = False
    echo_times: tuple[float, ...] = ()
    gradient: float = 0.0
    jz_initial: float = 0.35
    jz_final: float | None = None
    ramp_duration: float = 0.0
    final_time: float = 1.0
    postselect_min_occ: int | None = None

    def jz_at(self, t: float) -> float:
        if self.jz_final is None or self.ramp_duration <= 0:
            return float(self.jz_initial)
        frac = min(max(float(t) / float(self.ramp_duration), 0.0), 1.0)
        return float((1.0 - frac) * self.jz_initial + frac * self.jz_final)

    def echo_crossed(self, t0: float, t1: float) -> bool:
        return any(float(t0) < e <= float(t1) for e in self.echo_times)

    def fields_at(self, graph: LatticeGraph, t: float) -> np.ndarray:
        return gradient_fields(graph, self.gradient, axis=0)

def apply_echo_x(spins: np.ndarray) -> np.ndarray:
    out = np.array(spins, copy=True)
    out[..., 1] *= -1.0
    out[..., 2] *= -1.0
    return out

def protocol_from_config(config, final_time: float) -> ControlProtocol:
    c = getattr(config, "controls", config)
    model = getattr(config, "model", None)
    jz0 = getattr(model, "jz", 0.35) if model is not None else 0.35
    return ControlProtocol(
        enabled=bool(getattr(c, "enabled", False)),
        echo_times=tuple(getattr(c, "echo_times", ()) or ()),
        gradient=float(getattr(c, "gradient", 0.0)),
        jz_initial=float(jz0),
        jz_final=getattr(c, "jz_final", None),
        ramp_duration=float(getattr(c, "ramp_duration", 0.0)),
        final_time=float(final_time),
        postselect_min_occ=getattr(c, "postselect_min_occ", None),
    )
