from __future__ import annotations
from pathlib import Path
import sys, time, json, yaml
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from haxs.io.result_store import ensure_dir, save_dataframe, save_json
from haxs.lattice.graphs import hypercubic_lattice
from haxs.methods.dtwa import run_dtwa
from haxs.models.controls import ControlProtocol
from haxs.observables.diagnostics import bootstrap_ci


def load_raw_config(path: str | Path) -> dict:
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    return yaml.safe_load(p.read_text())


def seed_list(stage2: dict) -> list[int]:
    seeds = stage2.get('seeds', None)
    if isinstance(seeds, int):
        start = int(stage2.get('seed_start', 1001))
        return list(range(start, start + seeds))
    if isinstance(seeds, list):
        return [int(x) for x in seeds]
    return [int(stage2.get('seed', 1001))]


def baseline_control(raw: dict, t_final: float) -> ControlProtocol:
    return ControlProtocol(enabled=False, jz_initial=float(raw.get('model', {}).get('jz', 0.35)), final_time=float(t_final))


def dtwa_best_for_shape(raw: dict, shape: list[int] | tuple[int, ...], seeds: list[int], overrides: dict | None = None) -> pd.DataFrame:
    cfg = json.loads(json.dumps(raw))
    model = cfg.setdefault('model', {})
    if overrides:
        model.update(overrides)
    graph = hypercubic_lattice(tuple(shape), cfg.get('lattice', {}).get('periodic', False))
    dtwa = cfg.get('dtwa', {})
    times = np.linspace(0.0, float(dtwa.get('t_max', 1.3)), int(dtwa.get('n_steps', 31)))
    rows = []
    for s in seeds:
        ctrl = baseline_control(cfg, float(times[-1]))
        t0 = time.perf_counter()
        res = run_dtwa(
            graph, times,
            j_perp=float(model.get('j_perp', 1.0)),
            jz=float(model.get('jz', 0.35)),
            hole_fraction=float(model.get('hole_fraction', 0.18)),
            mobile_eta=float(model.get('mobile_eta', 0.55)),
            lambda_sd=float(model.get('lambda_sd', 0.30)),
            n_traj=int(dtwa.get('n_traj', 64)),
            seed=int(s), control=ctrl,
        )
        elapsed = time.perf_counter() - t0
        data = res['data']
        idx = int(np.nanargmin(data[:, 4]))
        rows.append({
            'seed': int(s), 'shape': 'x'.join(map(str, shape)), 'dimension': len(shape), 'N': int(graph.n_sites),
            'xi2_min': float(data[idx,4]), 'xi2_db_min': float(data[idx,5]), 'time_at_min': float(data[idx,0]),
            'spin_length_at_min': float(data[idx,7]), 'N_eff': float(data[idx,8]),
            'active_bonds': float(data[idx,9]), 'hole_spin_covariance': float(data[idx,10]),
            'runtime_seconds': float(elapsed),
            'jz': float(model.get('jz', 0.35)), 'hole_fraction': float(model.get('hole_fraction', 0.18)),
            'mobile_eta': float(model.get('mobile_eta', 0.55)), 'lambda_sd': float(model.get('lambda_sd', 0.30)),
        })
    return pd.DataFrame(rows)


def summary_with_ci(df: pd.DataFrame, group_cols: list[str], value: str, seed: int, n_boot: int) -> pd.DataFrame:
    rows = []
    for keys, g in df.groupby(group_cols, dropna=False):
        keys = keys if isinstance(keys, tuple) else (keys,)
        mean, lo, hi = bootstrap_ci(g[value].to_numpy(), seed=seed, n_boot=n_boot)
        row = dict(zip(group_cols, keys))
        row.update({'metric': value, 'mean': mean, 'ci90_low': lo, 'ci90_high': hi, 'std': float(g[value].std(ddof=1)) if len(g)>1 else 0.0, 'n': int(len(g))})
        rows.append(row)
    return pd.DataFrame(rows)
