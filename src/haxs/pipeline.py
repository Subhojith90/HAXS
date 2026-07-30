from __future__ import annotations
from pathlib import Path
import json
import numpy as np
import pandas as pd
from haxs.config.load import config_hash
from haxs.config.schema import RunConfig
from haxs.lattice.graphs import hypercubic_lattice
from haxs.models.controls import protocol_from_config, ControlProtocol
from haxs.methods.dtwa import run_dtwa
from haxs.io.result_store import ensure_dir, save_json


def _cfg_to_dict(cfg: RunConfig) -> dict:
    if getattr(cfg, 'raw', None):
        return dict(cfg.raw)
    return {
        'seed': cfg.seed,
        'level': cfg.level,
        'lattice': {'shape': list(cfg.lattice.shape), 'periodic': cfg.lattice.periodic},
        'model': {
            'j_perp': cfg.model.j_perp,
            'jz': cfg.model.jz,
            'hole_fraction': cfg.model.hole_fraction,
            'mobile_eta': cfg.model.mobile_eta,
            'lambda_sd': cfg.model.lambda_sd,
            'fixed_hole_count': cfg.model.fixed_hole_count,
        },
        'dtwa': {'n_traj': cfg.dtwa.n_traj, 't_max': cfg.dtwa.t_max, 'n_steps': cfg.dtwa.n_steps},
        'controls': {
            'enabled': cfg.controls.enabled,
            'echo_times': list(cfg.controls.echo_times),
            'gradient': cfg.controls.gradient,
            'jz_final': cfg.controls.jz_final,
            'ramp_duration': cfg.controls.ramp_duration,
            'postselect_min_occ': cfg.controls.postselect_min_occ,
        },
    }


def run_config(cfg: RunConfig, out_dir: str | Path, label: str | None = None, seed: int | None = None, control: ControlProtocol | None = None) -> dict[str, object]:
    """Run one DTWA/surrogate configuration and persist curve, summary, config and occupancies."""
    out = ensure_dir(out_dir)
    run_seed = int(cfg.seed if seed is None else seed)
    run_label = label or Path(str(out_dir)).name
    graph = hypercubic_lattice(cfg.lattice.shape, cfg.lattice.periodic)
    times = np.linspace(0.0, float(cfg.dtwa.t_max), int(cfg.dtwa.n_steps))
    ctrl = control if control is not None else protocol_from_config(cfg, float(times[-1]))
    result = run_dtwa(
        graph,
        times,
        j_perp=float(cfg.model.j_perp),
        jz=float(cfg.model.jz),
        hole_fraction=float(cfg.model.hole_fraction),
        mobile_eta=float(cfg.model.mobile_eta),
        lambda_sd=float(cfg.model.lambda_sd),
        n_traj=int(cfg.dtwa.n_traj),
        seed=run_seed,
        control=ctrl,
        fixed_hole_count=cfg.model.fixed_hole_count,
    )
    cols = [str(c) for c in result['columns']]
    df = pd.DataFrame(np.asarray(result['data']), columns=cols)
    df['label'] = run_label
    df['seed'] = run_seed
    df['dimension'] = graph.dim
    df['N_sites'] = graph.n_sites
    df['p_hole_requested'] = float(cfg.model.hole_fraction)
    df['mobile_eta'] = float(cfg.model.mobile_eta)
    df['lambda_sd'] = float(cfg.model.lambda_sd)
    cfg_dict = _cfg_to_dict(cfg)
    h = config_hash(cfg)
    df['config_hash'] = h
    curve_path = out / f'{run_label}_curve.csv'
    df.to_csv(curve_path, index=False)
    best_idx = int(np.nanargmin(df['xi2'].to_numpy()))
    best = df.iloc[best_idx]
    summary = {
        'label': run_label,
        'seed': run_seed,
        'level': cfg.level,
        'dimension': graph.dim,
        'N_sites': graph.n_sites,
        'N_eff_mean': float(df['N_eff'].mean()),
        'hole_fraction_requested': float(cfg.model.hole_fraction),
        'mobile_eta': float(cfg.model.mobile_eta),
        'lambda_sd': float(cfg.model.lambda_sd),
        'jz': float(cfg.model.jz),
        'n_traj': int(cfg.dtwa.n_traj),
        't_max': float(cfg.dtwa.t_max),
        'n_steps': int(cfg.dtwa.n_steps),
        'best_time': float(best['time']),
        'best_xi2': float(best['xi2']),
        'best_xi2_db': float(best['xi2_db']),
        'best_spin_length': float(best['spin_length']),
        'final_xi2_db': float(df['xi2_db'].iloc[-1]),
        'active_bonds_mean': float(df['active_bonds'].mean()),
        'field_rms': float(df.get('field_rms', pd.Series([0.0])).mean()) if 'field_rms' in df else 0.0,
        'config_hash': h,
        'csv_path': str(curve_path),
    }
    save_json(out / f'{run_label}_summary.json', summary)
    (out / f'{run_label}_config.json').write_text(json.dumps(cfg_dict, indent=2, default=str), encoding='utf-8')
    np.savetxt(out / f'{run_label}_initial_occupancy.txt', np.asarray(result['initial_occupancy'], dtype=int), fmt='%d')
    return {'graph': graph, 'result': result, 'dataframe': df, 'summary': summary, 'curve_path': curve_path}
