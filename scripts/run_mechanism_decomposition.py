#!/usr/bin/env python
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

import argparse, yaml, json
import numpy as np
import pandas as pd
from haxs.config.load import load_config
from haxs.lattice.graphs import hypercubic_lattice
from haxs.methods.dtwa import run_dtwa
from haxs.models.controls import ControlProtocol
from haxs.observables.diagnostics import mechanism_distance, curve_sensitivity_table
from haxs.io.result_store import ensure_dir, save_dataframe, save_json
from haxs.utils.logging import append_log

ap=argparse.ArgumentParser(); ap.add_argument('--config', required=True); ap.add_argument('--out', default='results/paper_lite/mechanism'); args=ap.parse_args()
out=ensure_dir(ROOT/args.out); cfg=load_config(ROOT/args.config if not str(args.config).startswith('/') else args.config); raw=cfg.raw
g=hypercubic_lattice(cfg.lattice.shape,cfg.lattice.periodic); times=np.linspace(0,cfg.dtwa.t_max,cfg.dtwa.n_steps)
seeds=raw.get('mechanism',{}).get('seeds',[cfg.seed])
base_model=raw.get('model',{})
cases={
 'ideal': {'hole_fraction':0.0,'mobile_eta':0.0,'lambda_sd':0.0},
 'static_vacancies': {'hole_fraction':cfg.model.hole_fraction,'mobile_eta':0.0,'lambda_sd':0.0},
 'mobile_only': {'hole_fraction':cfg.model.hole_fraction,'mobile_eta':cfg.model.mobile_eta,'lambda_sd':0.0},
 'spin_density_static': {'hole_fraction':cfg.model.hole_fraction,'mobile_eta':0.0,'lambda_sd':cfg.model.lambda_sd},
 'full_mobile_sd': {'hole_fraction':cfg.model.hole_fraction,'mobile_eta':cfg.model.mobile_eta,'lambda_sd':cfg.model.lambda_sd},
}
records=[]
for label, params in cases.items():
    for s in seeds:
        ctrl=ControlProtocol(enabled=False,jz_initial=cfg.model.jz,final_time=float(times[-1]))
        res=run_dtwa(g,times,cfg.model.j_perp,cfg.model.jz,params['hole_fraction'],params['mobile_eta'],params['lambda_sd'],cfg.dtwa.n_traj,int(s),ctrl)
        df=pd.DataFrame(res['data'],columns=res['columns']); df['label']=label; df['seed']=int(s); records.append(df)
all_df=pd.concat(records, ignore_index=True); save_dataframe(out/'mechanism_curves_all.csv', all_df, raw)
mean_df=all_df.groupby(['label','time'], as_index=False).agg({c:'mean' for c in ['Sx','Sy','Sz','xi2','xi2_db','min_var','spin_length','N_eff','active_bonds','hole_spin_covariance']})
save_dataframe(out/'mechanism_curves_mean.csv', mean_df, raw)
curves={lab:grp.sort_values('time')['xi2_db'].to_numpy() for lab,grp in mean_df.groupby('label')}
dists=curve_sensitivity_table(curves)
summary={'mean_full_vs_static_distance_db': float(dists.get('distance_static_vacancies_vs_full_mobile_sd', mechanism_distance(curves.get('static_vacancies',[]), curves.get('full_mobile_sd',[])))), 'distances': dists, 'seeds': seeds, 'n_sites': g.n_sites}
save_json(out/'mechanism_summary.json', summary)
ensure_dir(ROOT/'tables/paper_lite'); save_dataframe(ROOT/'tables/paper_lite/mechanism_summary.csv', pd.DataFrame([{'metric':k,'value':v} for k,v in summary.items() if isinstance(v,(int,float))]), raw)
append_log(ROOT/'reproducibility/run_log.md', f'mechanism decomposition wrote {out}')
with (ROOT/'reproducibility/command_history.sh').open('a', encoding='utf-8') as f: f.write(f'python scripts/run_mechanism_decomposition.py --config {args.config} --out {args.out}\n')
print(f'mechanism decomposition wrote {out}')
