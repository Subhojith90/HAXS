from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)
class LatticeConfig:
    shape: tuple[int, ...] = (8,)
    periodic: bool = False

@dataclass(frozen=True)
class ModelConfig:
    j_perp: float = 1.0
    jz: float = 0.35
    hole_fraction: float = 0.0
    mobile_eta: float = 0.0
    lambda_sd: float = 0.0
    fixed_hole_count: int | None = None

@dataclass(frozen=True)
class DTWAConfig:
    n_traj: int = 64
    t_max: float = 1.2
    n_steps: int = 25

@dataclass(frozen=True)
class ControlConfig:
    enabled: bool = False
    echo_times: tuple[float, ...] = ()
    gradient: float = 0.0
    jz_final: float | None = None
    ramp_duration: float = 0.0
    postselect_min_occ: int | None = None

@dataclass(frozen=True)
class RunConfig:
    seed: int = 1729
    level: str = "smoke"
    lattice: LatticeConfig = field(default_factory=LatticeConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    dtwa: DTWAConfig = field(default_factory=DTWAConfig)
    controls: ControlConfig = field(default_factory=ControlConfig)
    raw: dict[str, Any] = field(default_factory=dict)

def run_config_from_dict(data: dict[str, Any]) -> RunConfig:
    lat = data.get("lattice", {})
    mod = data.get("model", {})
    dtw = data.get("dtwa", {})
    ctrl = data.get("controls", {})
    return RunConfig(
        seed=int(data.get("seed", 1729)),
        level=str(data.get("level", "smoke")),
        lattice=LatticeConfig(shape=tuple(int(x) for x in lat.get("shape", [8])), periodic=bool(lat.get("periodic", False))),
        model=ModelConfig(
            j_perp=float(mod.get("j_perp", 1.0)),
            jz=float(mod.get("jz", 0.35)),
            hole_fraction=float(mod.get("hole_fraction", 0.0)),
            mobile_eta=float(mod.get("mobile_eta", 0.0)),
            lambda_sd=float(mod.get("lambda_sd", 0.0)),
            fixed_hole_count=mod.get("fixed_hole_count"),
        ),
        dtwa=DTWAConfig(n_traj=int(dtw.get("n_traj", 64)), t_max=float(dtw.get("t_max", 1.2)), n_steps=int(dtw.get("n_steps", 25))),
        controls=ControlConfig(
            enabled=bool(ctrl.get("enabled", False)),
            echo_times=tuple(float(x) for x in ctrl.get("echo_times", []) or []),
            gradient=float(ctrl.get("gradient", 0.0)),
            jz_final=None if ctrl.get("jz_final", None) is None else float(ctrl.get("jz_final")),
            ramp_duration=float(ctrl.get("ramp_duration", 0.0)),
            postselect_min_occ=ctrl.get("postselect_min_occ"),
        ),
        raw=data,
    )
