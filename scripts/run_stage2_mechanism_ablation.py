#!/usr/bin/env python
from pathlib import Path
import argparse, pandas as pd, numpy as np
from stage2_common import ROOT, load_raw_config, seed_list
from haxs.lattice.graphs import hypercubic_lattice
from haxs.methods.dtwa import run_dtwa
from haxs.models.controls import ControlProtocol
from haxs.observables.diagnostics import mechanism_distance, curve_sensitivity_table, bootstrap_ci
from haxs.io.result_store import ensure_dir, save_dataframe, save_json

ap=argparse.ArgumentParser(); ap.add_argument('--config', default='configs/stage2_lite/mechanism_ablation.yaml'); ap.add_argument('--out', default='results/stage2_lite/mechanism_ablation'); args=ap.parse_args()
raw=load_raw_config(args.config); out=ensure_dir(ROOT/args.out)
shape=raw.get('lattice',{}).get('shape',[3,3,3]); model=raw.get('model',{}); dtwa=raw.get('dtwa',{}); seeds=seed_list(raw.get('mechanism',{}))
g=hypercubic_lattice(tuple(shape), raw.get('lattice',{}).get('periodic',False)); times=np.linspace(0,float(dtwa.get('t_max',1.6)),int(dtwa.get('n_steps',41)))
base={'hole_fraction':float(model.get('hole_fraction',0.18)), 'mobile_eta':float(model.get('mobile_eta',0.55)), 'lambda_sd':float(model.get('lambda_sd',0.30))}
cases={
 'ideal_clean': {'hole_fraction':0.0,'mobile_eta':0.0,'lambda_sd':0.0, 'control':'off'},
 'static_only': {'hole_fraction':base['hole_fraction'],'mobile_eta':0.0,'lambda_sd':0.0, 'control':'off'},
 'mobile_only': {'hole_fraction':base['hole_fraction'],'mobile_eta':base['mobile_eta'],'lambda_sd':0.0, 'control':'off'},
 'spin_density_only': {'hole_fraction':base['hole_fraction'],'mobile_eta':0.0,'lambda_sd':base['lambda_sd'], 'control':'off'},
 'mobile_plus_spin_density': {'hole_fraction':base['hole_fraction'],'mobile_eta':base['mobile_eta'],'lambda_sd':base['lambda_sd'], 'control':'off'},
 'echo_only': {'hole_fraction':base['hole_fraction'],'mobile_eta':base['mobile_eta'],'lambda_sd':base['lambda_sd'], 'control':'echo'},
 'gradient_only': {'hole_fraction':base['hole_fraction'],'mobile_eta':base['mobile_eta'],'lambda_sd':base['lambda_sd'], 'control':'gradient'},
 'ramp_only': {'hole_fraction':base['hole_fraction'],'mobile_eta':base['mobile_eta'],'lambda_sd':base['lambda_sd'], 'control':'ramp'},
 'echo_gradient': {'hole_fraction':base['hole_fraction'],'mobile_eta':base['mobile_eta'],'lambda_sd':base['lambda_sd'], 'control':'echo_gradient'},
 'everything': {'hole_fraction':base['hole_fraction'],'mobile_eta':base['mobile_eta'],'lambda_sd':base['lambda_sd'], 'control':'everything'},
}

def ctrl(kind):
    jz=float(model.get('jz',0.35)); t=float(times[-1])
    if kind=='off': return ControlProtocol(enabled=False,jz_initial=jz,final_time=t)
    return ControlProtocol(enabled=True, echo_times=(0.5*t,) if 'echo' in kind or kind=='everything' else tuple(), gradient=0.12 if 'gradient' in kind or kind=='everything' else 0.0, jz_initial=jz, jz_final=0.15 if 'ramp' in kind or kind=='everything' else jz, ramp_duration=0.35*t if 'ramp' in kind or kind=='everything' else 0.0, final_time=t)

records=[]
for label,p in cases.items():
    for s in seeds:
        res=run_dtwa(g,times,j_perp=float(model.get('j_perp',1.0)),jz=float(model.get('jz',0.35)),hole_fraction=p['hole_fraction'],mobile_eta=p['mobile_eta'],lambda_sd=p['lambda_sd'],n_traj=int(dtwa.get('n_traj',96)),seed=int(s),control=ctrl(p['control']))
        df=pd.DataFrame(res['data'],columns=res['columns']); df['label']=label; df['seed']=int(s); df['control_case']=p['control']; records.append(df)
all_df=pd.concat(records, ignore_index=True)
mean_df=all_df.groupby(['label','time'], as_index=False).agg({c:'mean' for c in ['Sx','Sy','Sz','xi2','xi2_db','min_var','spin_length','N_eff','active_bonds','hole_spin_covariance']})
finals=all_df.loc[all_df.groupby(['label','seed'])['xi2_db'].idxmin()].copy().rename(columns={'xi2_db':'xi2_db_min','time':'time_at_min'})
curves={lab:gdf.sort_values('time')['xi2_db'].to_numpy() for lab,gdf in mean_df.groupby('label')}
dists=curve_sensitivity_table(curves)
summary_rows=[]
for lab,gdf in finals.groupby('label'):
    mean,lo,hi=bootstrap_ci(gdf['xi2_db_min'].to_numpy(), seed=int(raw.get('seed',1729)), n_boot=400)
    summary_rows.append({'label':lab,'mean_xi2_db_min':mean,'ci90_low':lo,'ci90_high':hi,'std':float(gdf['xi2_db_min'].std(ddof=1)) if len(gdf)>1 else 0.0,'n':int(len(gdf))})
summary=pd.DataFrame(summary_rows)
save_dataframe(out/'mechanism_ablation_curves_all.csv', all_df, raw); save_dataframe(out/'mechanism_ablation_curves_mean.csv', mean_df, raw); save_dataframe(out/'mechanism_ablation_finals.csv', finals, raw); save_dataframe(out/'mechanism_ablation_summary.csv', summary, raw); save_dataframe(out/'mechanism_distances.csv', pd.DataFrame([{'distance':k,'value':v} for k,v in dists.items()]), raw)
save_json(out/'mechanism_ablation_manifest.json', {'config':args.config,'n_cases':len(cases),'n_seeds':len(seeds),'shape':shape})
print(f'stage2 mechanism ablation wrote {out}; cases={len(cases)} rows={len(all_df)}')
