#!/usr/bin/env python
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src')); sys.path.insert(0,str(ROOT/'scripts'))
from stage2_common import load_raw_config
from stage5c2eR_common import domain_seed, sha_arr
from haxs.lattice.graphs import hypercubic_lattice
from haxs.methods.dtwa import run_dtwa
from haxs.models.controls import ControlProtocol
from haxs.io.result_store import ensure_dir, save_dataframe, save_json
from haxs.io.hashes import hash_dict


def label_params(label, model):
    if label == 'static_only': return {'mobile_eta':0.0,'lambda_sd':0.0}
    if label == 'mobile_plus_spin_density': return {'mobile_eta':float(model.get('mobile_eta',0.55)),'lambda_sd':float(model.get('lambda_sd',0.30))}
    raise ValueError(label)


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--config',default='configs/stage5c2eR/five_hole_diagnostic.yaml'); ap.add_argument('--out',default='results/stage5c2eR/fixed_count_diagnostic'); ap.add_argument('--dry-run',action='store_true')
    a=ap.parse_args(); raw=load_raw_config(a.config); st=raw['stage5c2eR_fixed_count']; model=raw['model']; dtwa=raw['dtwa']
    shape=tuple(st['shape']); labels=list(st['labels']); I=int(st['occupancies']); J=int(st['paths_per_occupancy']); K=int(st['phase_batches_per_path']); n_traj=int(st.get('n_traj',1024)); n_holes=int(st['fixed_hole_count'])
    if a.dry_run:
        print(f'DRY RUN Stage 5C.2E-R fixed-count diagnostic: shape={"x".join(map(str,shape))} fixed_holes={n_holes} I={I} J={J} K={K} labels={labels} runs={I*J*K*len(labels)}')
        return
    out=ensure_dir(ROOT/a.out); graph=hypercubic_lattice(shape, raw.get('lattice',{}).get('periodic',False))
    times=np.linspace(0,float(dtwa.get('t_max',1.4)),int(dtwa.get('n_steps',45)))
    fixed_idx=max(0,min(len(times)-1,int(round(float(st.get('fixed_time_fraction',0.65))*(len(times)-1)))))
    fixed_time=float(times[fixed_idx]); ctrl=ControlProtocol(enabled=False,jz_initial=float(model.get('jz',0.35)),final_time=float(times[-1])); ns=st.get('seed_namespace','stage5c2eR_fixed_five_hole_diagnostic_v1')
    curves=[]; finals=[]; registry=[]
    for oi in range(I):
        occ_seed=domain_seed(ns,'occupancy',oi)
        for pj in range(J):
            path_seed=domain_seed(ns,'path',oi,pj)
            for pk in range(K):
                phase_seed=domain_seed(ns,'phase',oi,pj,pk)
                for label in labels:
                    lp=label_params(label,model); actual_path=path_seed if label=='mobile_plus_spin_density' else 0; rid=f'fixed5_occ{oi:03d}_path{pj:02d}_phase{pk:02d}_{label}'
                    t0=time.perf_counter(); res=run_dtwa(graph,times,j_perp=float(model.get('j_perp',1.0)),jz=float(model.get('jz',0.35)),hole_fraction=float(model.get('hole_fraction',0.18)),fixed_hole_count=n_holes,mobile_eta=lp['mobile_eta'],lambda_sd=lp['lambda_sd'],n_traj=n_traj,seed=phase_seed,control=ctrl,occupancy_seed=occ_seed,hole_path_seed=actual_path,phase_batch_seed=phase_seed); elapsed=time.perf_counter()-t0
                    df=pd.DataFrame(res['data'],columns=res['columns']); occ_hash=sha_arr(res['initial_occupancy']); path_hash=sha_arr(res['occupancy_trajectory'])
                    df['stage']='stage5c2eR_fixed_count'; df['block']='fixed_count_diagnostic'; df['shape']='x'.join(map(str,shape)); df['N']=int(graph.n_sites); df['label']=label; df['occupancy_idx']=oi; df['path_idx']=pj; df['phase_idx']=pk; df['occupancy_seed']=occ_seed; df['hole_path_seed']=actual_path; df['phase_batch_seed']=phase_seed; df['occupancy_hash']=occ_hash; df['path_hash']=path_hash; df['n_holes']=n_holes; df['run_id']=rid; curves.append(df)
                    best_i=int(np.nanargmin(df['xi2_db'].to_numpy(float))); fixed=df.iloc[fixed_idx]; best=df.iloc[best_i]
                    finals.append({'stage':'stage5c2eR_fixed_count','block':'fixed_count_diagnostic','shape':'x'.join(map(str,shape)),'N':int(graph.n_sites),'label':label,'occupancy_idx':oi,'path_idx':pj,'phase_idx':pk,'occupancy_seed':occ_seed,'hole_path_seed':actual_path,'phase_batch_seed':phase_seed,'occupancy_hash':occ_hash,'path_hash':path_hash,'n_holes':n_holes,'run_id':rid,'xi2_db_fixed':float(fixed['xi2_db']),'xi2_db_min':float(best['xi2_db']),'fixed_time':fixed_time,'time_at_min':float(best['time']),'N_eff_fixed':float(fixed['N_eff']),'active_bonds_fixed':float(fixed['active_bonds']),'runtime_seconds':elapsed})
                    registry.append({'block':'fixed_count_diagnostic','occupancy_idx':oi,'path_idx':pj,'phase_idx':pk,'label':label,'occupancy_seed':occ_seed,'hole_path_seed':actual_path,'phase_batch_seed':phase_seed,'occupancy_hash':occ_hash,'path_hash':path_hash,'n_holes':n_holes,'run_id':rid})
    save_dataframe(out/'stage5c2eR_fixed_count_curves_all.csv',pd.concat(curves,ignore_index=True),raw)
    save_dataframe(out/'stage5c2eR_fixed_count_finals.csv',pd.DataFrame(finals),raw)
    save_dataframe(out/'stage5c2eR_fixed_count_seed_registry.csv',pd.DataFrame(registry),raw)
    save_json(out/'stage5c2eR_fixed_count_manifest.json',{'stage':'stage5c2eR_fixed_count_diagnostic','config':a.config,'config_hash':hash_dict(raw),'shape':list(shape),'fixed_hole_count':n_holes,'occupancies':I,'paths_per_occupancy':J,'phase_batches_per_path':K,'n_traj':n_traj,'claim_scope':st.get('claim_scope','')})
    print(f'Stage 5C.2E-R fixed-count diagnostic wrote {out}; finals={len(finals)}')
if __name__=='__main__': main()
