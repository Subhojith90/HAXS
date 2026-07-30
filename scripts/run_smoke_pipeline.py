#!/usr/bin/env python
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

import argparse, json, yaml
import numpy as np
import pandas as pd
from haxs.config.load import load_config
from haxs.lattice.graphs import hypercubic_lattice
from haxs.methods.dtwa import run_dtwa, curve_to_records
from haxs.models.controls import protocol_from_config
from haxs.optimize.splits import train_test_seeds
from haxs.optimize.random_search import random_search
from haxs.optimize.objectives import evaluate_protocol, baseline_theta
from haxs.nogo.thresholds import threshold_scan, ph_star_table
from haxs.io.result_store import ensure_dir, save_dataframe, save_json
from haxs.utils.logging import append_log

def times_from_cfg(cfg):
    return np.linspace(0.0, cfg.dtwa.t_max, cfg.dtwa.n_steps)

ap = argparse.ArgumentParser(); ap.add_argument('--out', default='results/smoke'); args = ap.parse_args()
out = ensure_dir(ROOT / args.out); rows=[]; all_records=[]
for cp in sorted((ROOT/'configs/smoke').glob('*.yaml')):
    if cp.name in {'robust_optimization_smoke.yaml','threshold_map_smoke.yaml'}:
        continue
    cfg = load_config(cp); g = hypercubic_lattice(cfg.lattice.shape, cfg.lattice.periodic); t = times_from_cfg(cfg)
    ctrl = protocol_from_config(cfg, float(t[-1]))
    res = run_dtwa(g, t, cfg.model.j_perp, cfg.model.jz, cfg.model.hole_fraction, cfg.model.mobile_eta, cfg.model.lambda_sd, cfg.dtwa.n_traj, cfg.seed, ctrl, cfg.model.fixed_hole_count)
    df = pd.DataFrame(res['data'], columns=res['columns']); df['run'] = cp.stem; df['seed'] = cfg.seed
    save_dataframe(out / f'{cp.stem}_curve.csv', df, cfg.raw)
    all_records.append(df)
    rows.append({'run':cp.stem,'n_sites':g.n_sites,'min_xi2_db':float(df.xi2_db.min()),'final_xi2_db':float(df.xi2_db.iloc[-1]),'min_spin_length':float(df.spin_length.min()),'config':str(cp.relative_to(ROOT))})
# smoke optimization
opt_path = ROOT/'configs/smoke/robust_optimization_smoke.yaml'
raw = yaml.safe_load(opt_path.read_text())
split = train_test_seeds(int(raw['seed']), raw['optimization']['n_train'], raw['optimization']['n_test'])
base = evaluate_protocol(raw, baseline_theta(raw['dtwa']['t_max']), split['test'])
search = random_search(raw, split['train'], raw['optimization']['n_candidates'], raw['seed'])
best_train = search[0]
best_test = evaluate_protocol(raw, best_train['theta'], split['test'])
save_dataframe(out/'control_scan.csv', pd.DataFrame([{'rank':i, 'objective':r['objective'], 'mean_xi2_db':r['mean_xi2_db'], **r['theta']} for i,r in enumerate(search)]), raw)
save_json(out/'control_scan_summary.json', {'baseline_test':base, 'best_train':best_train, 'best_test':best_test, 'train_seeds':split['train'], 'test_seeds':split['test']})
# smoke threshold
th_path = ROOT/'configs/smoke/threshold_map_smoke.yaml'; raw_th = yaml.safe_load(th_path.read_text())
th = threshold_scan(raw_th); pstar = ph_star_table(th)
save_dataframe(out/'threshold_map_smoke.csv', th, raw_th); save_dataframe(out/'pstar_smoke.csv', pstar, raw_th)
summary = pd.DataFrame(rows); save_dataframe(out/'smoke_summary.csv', summary)
# mirror to tables
ensure_dir(ROOT/'tables/smoke')
save_dataframe(ROOT/'tables/smoke/smoke_summary.csv', summary)
append_log(ROOT/'reproducibility/run_log.md', f'smoke pipeline wrote {out}')
with (ROOT/'reproducibility/command_history.sh').open('a', encoding='utf-8') as f: f.write('python scripts/run_smoke_pipeline.py --out results/smoke\n')
print(f'smoke pipeline wrote {out}')
