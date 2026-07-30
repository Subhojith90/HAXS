
#!/usr/bin/env python
from __future__ import annotations
import argparse, json, sys, time, hashlib
from pathlib import Path
import numpy as np
import pandas as pd
import yaml
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src')); sys.path.insert(0, str(ROOT/'scripts'))
from stage2_common import load_raw_config
from haxs.lattice.graphs import hypercubic_lattice
from haxs.methods.dtwa import run_dtwa
from haxs.models.controls import ControlProtocol
from haxs.io.result_store import ensure_dir, save_dataframe, save_json
from haxs.io.hashes import hash_dict


def sha_arr(a) -> str:
    return hashlib.sha256(np.asarray(a, dtype=np.int8).tobytes()).hexdigest()[:16]

def label_params(label, model):
    if label == 'static_only':
        return {'hole_fraction': float(model.get('hole_fraction', 0.18)), 'mobile_eta': 0.0, 'lambda_sd': 0.0}
    if label == 'mobile_plus_spin_density':
        return {'hole_fraction': float(model.get('hole_fraction', 0.18)), 'mobile_eta': float(model.get('mobile_eta', 0.55)), 'lambda_sd': float(model.get('lambda_sd', 0.30))}
    raise ValueError(f'Stage 5C.2D only supports core labels, got {label}')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', default='configs/stage5c2d_lite/nested_core_3x3x3.yaml')
    ap.add_argument('--block', required=True, choices=['primary','confirmation'])
    ap.add_argument('--out', required=True)
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    raw = load_raw_config(a.config); st = raw['stage5c2d']; model = raw['model']; dtwa = raw['dtwa']
    if a.block not in st['blocks']:
        raise SystemExit(f'unknown block {a.block}')
    bcfg = st['blocks'][a.block]
    out = ensure_dir(ROOT/a.out)
    shape = tuple(st['shape']); graph = hypercubic_lattice(shape, raw.get('lattice',{}).get('periodic', False))
    times = np.linspace(0, float(dtwa.get('t_max', 1.4)), int(dtwa.get('n_steps', 45)))
    fixed_idx = max(0, min(len(times)-1, int(round(float(st.get('fixed_time_fraction', 0.65))*(len(times)-1)))))
    fixed_time = float(times[fixed_idx])
    n_occ = int(st.get('occupancy_realizations', 12)); n_path = int(st.get('paths_per_occupancy', 4)); n_phase = int(st.get('phase_batches_per_path', 4)); n_traj = int(st.get('n_traj', dtwa.get('n_traj', 1024)))
    labels = list(st.get('labels', ['static_only','mobile_plus_spin_density']))
    commands = []
    if a.dry_run:
        print(f'DRY RUN Stage 5C.2D block={a.block} shape={"x".join(map(str,shape))} labels={labels} occupancy={n_occ} paths={n_path} phase_batches={n_phase} n_traj={n_traj}')
        return
    curves=[]; finals=[]; registry=[]
    ctrl = ControlProtocol(enabled=False, jz_initial=float(model.get('jz',0.35)), final_time=float(times[-1]))
    for oi in range(n_occ):
        occupancy_seed = int(bcfg['occupancy_seed_start']) + oi
        for pj in range(n_path):
            hole_path_seed = int(bcfg['hole_path_seed_start']) + oi*1000 + pj
            for pk in range(n_phase):
                phase_batch_seed = int(bcfg['phase_batch_seed_start']) + oi*100000 + pj*1000 + pk
                for label in labels:
                    lp = label_params(label, model)
                    path_seed = hole_path_seed if label == 'mobile_plus_spin_density' else 0
                    run_id = f'{a.block}_occ{oi:03d}_path{pj:02d}_phase{pk:02d}_{label}'
                    t0=time.perf_counter()
                    res = run_dtwa(graph, times, j_perp=float(model.get('j_perp',1.0)), jz=float(model.get('jz',0.35)), hole_fraction=lp['hole_fraction'], mobile_eta=lp['mobile_eta'], lambda_sd=lp['lambda_sd'], n_traj=n_traj, seed=phase_batch_seed, control=ctrl, occupancy_seed=occupancy_seed, hole_path_seed=path_seed, phase_batch_seed=phase_batch_seed)
                    elapsed=time.perf_counter()-t0
                    df=pd.DataFrame(res['data'], columns=res['columns'])
                    occ_hash = sha_arr(res['initial_occupancy']); path_hash = sha_arr(res['occupancy_trajectory'])
                    df['stage']='stage5c2d'; df['block']=a.block; df['shape']='x'.join(map(str,shape)); df['N']=int(graph.n_sites); df['label']=label; df['occupancy_idx']=oi; df['path_idx']=pj; df['phase_idx']=pk; df['occupancy_seed']=occupancy_seed; df['hole_path_seed']=path_seed; df['phase_batch_seed']=phase_batch_seed; df['occupancy_hash']=occ_hash; df['path_hash']=path_hash; df['run_id']=run_id
                    curves.append(df)
                    best_i=int(np.nanargmin(df['xi2_db'].to_numpy(float))); fixed=df.iloc[fixed_idx]; best=df.iloc[best_i]
                    finals.append({'stage':'stage5c2d','block':a.block,'shape':'x'.join(map(str,shape)),'N':int(graph.n_sites),'label':label,'occupancy_idx':oi,'path_idx':pj,'phase_idx':pk,'occupancy_seed':occupancy_seed,'hole_path_seed':path_seed,'phase_batch_seed':phase_batch_seed,'occupancy_hash':occ_hash,'path_hash':path_hash,'run_id':run_id,'xi2_db_fixed':float(fixed['xi2_db']),'xi2_db_min':float(best['xi2_db']),'fixed_time':fixed_time,'time_at_min':float(best['time']),'N_eff_fixed':float(fixed['N_eff']),'active_bonds_fixed':float(fixed['active_bonds']),'runtime_seconds':elapsed})
                    registry.append({'block':a.block,'occupancy_idx':oi,'path_idx':pj,'phase_idx':pk,'label':label,'occupancy_seed':occupancy_seed,'hole_path_seed':path_seed,'phase_batch_seed':phase_batch_seed,'occupancy_hash':occ_hash,'path_hash':path_hash,'run_id':run_id})
    curves_df=pd.concat(curves, ignore_index=True); finals_df=pd.DataFrame(finals); reg_df=pd.DataFrame(registry)
    save_dataframe(out/'stage5c2d_curves_all.csv', curves_df, raw)
    save_dataframe(out/'stage5c2d_finals.csv', finals_df, raw)
    save_dataframe(out/'stage5c2d_seed_registry.csv', reg_df, raw)
    save_json(out/'stage5c2d_block_manifest.json', {'stage':'stage5c2d_nested_core','block':a.block,'config':a.config,'config_hash':hash_dict(raw),'shape':list(shape),'labels':labels,'fixed_time':fixed_time,'occupancy_realizations':n_occ,'paths_per_occupancy':n_path,'phase_batches_per_path':n_phase,'n_traj':n_traj,'claim_scope':st.get('claim_scope','')})
    print(f'Stage 5C.2D nested core wrote {out}; rows={len(curves_df)} finals={len(finals_df)}')

if __name__ == '__main__': main()
