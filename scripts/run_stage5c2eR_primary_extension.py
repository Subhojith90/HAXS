#!/usr/bin/env python
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src')); sys.path.insert(0, str(ROOT/'scripts'))
from stage2_common import load_raw_config
from stage5c2eR_common import domain_seed, sha_arr
from haxs.lattice.graphs import hypercubic_lattice
from haxs.methods.dtwa import run_dtwa
from haxs.models.controls import ControlProtocol
from haxs.io.result_store import ensure_dir, save_dataframe, save_json
from haxs.io.hashes import hash_dict


def label_params(label, model):
    if label == 'static_only':
        return {'hole_fraction': float(model.get('hole_fraction', 0.18)), 'mobile_eta': 0.0, 'lambda_sd': 0.0}
    if label == 'mobile_plus_spin_density':
        return {'hole_fraction': float(model.get('hole_fraction', 0.18)), 'mobile_eta': float(model.get('mobile_eta', 0.55)), 'lambda_sd': float(model.get('lambda_sd', 0.30))}
    raise ValueError(f'Stage 5C.2E-R only supports core labels, got {label}')


def _read_existing(existing: Path):
    finals = pd.read_csv(existing/'stage5c2d_finals.csv')
    curves = pd.read_csv(existing/'stage5c2d_curves_all.csv')
    registry = pd.read_csv(existing/'stage5c2d_seed_registry.csv')
    for df in (finals, curves, registry):
        df['stage5c2eR_source'] = 'locked_stage5c2d_primary'
    return finals, curves, registry


def _needed_cells(n_old_occ, j_old, n_occ, n_path, n_phase):
    out=[]
    for oi in range(n_occ):
        for pj in range(n_path):
            for pk in range(n_phase):
                if oi < n_old_occ and pj < j_old:
                    continue
                out.append((oi,pj,pk))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', default='configs/stage5c2eR/primary_I16_J6_K4.yaml')
    ap.add_argument('--existing-primary', required=True)
    ap.add_argument('--out', default='results/stage5c2eR/primary')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    raw = load_raw_config(a.config); st = raw['stage5c2eR']; model = raw['model']; dtwa = raw['dtwa']
    old = st['existing_design']; new = st['extended_design']
    n_old_occ = int(old['occupancies']); j_old = int(old['paths_per_occupancy'])
    n_occ = int(new['occupancies']); n_path = int(new['paths_per_occupancy']); n_phase = int(new['phase_batches_per_path'])
    cells = _needed_cells(n_old_occ, j_old, n_occ, n_path, n_phase)
    labels = list(st.get('labels', ['static_only','mobile_plus_spin_density']))
    if a.dry_run:
        print(f'DRY RUN Stage 5C.2E-R primary extension: existing=({n_old_occ},{j_old},{old["phase_batches_per_path"]}) target=({n_occ},{n_path},{n_phase}) new_cells={len(cells)} labels={labels} new_simulator_runs={len(cells)*len(labels)}')
        return
    existing = ROOT/a.existing_primary
    if not (existing/'stage5c2d_finals.csv').exists():
        raise FileNotFoundError(f'Missing existing primary finals: {existing}')
    old_finals, old_curves, old_registry = _read_existing(existing)
    out = ensure_dir(ROOT/a.out)
    shape = tuple(st['shape']); graph = hypercubic_lattice(shape, raw.get('lattice',{}).get('periodic', False))
    times = np.linspace(0, float(dtwa.get('t_max', 1.4)), int(dtwa.get('n_steps', 45)))
    fixed_idx = max(0, min(len(times)-1, int(round(float(st.get('fixed_time_fraction', 0.65))*(len(times)-1)))))
    fixed_time = float(times[fixed_idx])
    n_traj = int(st.get('n_traj', dtwa.get('n_traj', 1024)))
    namespace = st.get('seed_namespace','stage5c2eR_primary_extension_v1')
    ctrl = ControlProtocol(enabled=False, jz_initial=float(model.get('jz',0.35)), final_time=float(times[-1]))
    curves=[]; finals=[]; registry=[]
    for oi,pj,pk in cells:
        occupancy_seed = domain_seed(namespace, 'primary', 'occupancy', oi)
        hole_path_seed = domain_seed(namespace, 'primary', 'path', oi, pj)
        phase_batch_seed = domain_seed(namespace, 'primary', 'phase', oi, pj, pk)
        for label in labels:
            lp = label_params(label, model)
            path_seed = hole_path_seed if label == 'mobile_plus_spin_density' else 0
            run_id = f'primary_ext_occ{oi:03d}_path{pj:02d}_phase{pk:02d}_{label}'
            t0=time.perf_counter()
            res = run_dtwa(graph, times, j_perp=float(model.get('j_perp',1.0)), jz=float(model.get('jz',0.35)), hole_fraction=lp['hole_fraction'], mobile_eta=lp['mobile_eta'], lambda_sd=lp['lambda_sd'], n_traj=n_traj, seed=phase_batch_seed, control=ctrl, occupancy_seed=occupancy_seed, hole_path_seed=path_seed, phase_batch_seed=phase_batch_seed)
            elapsed=time.perf_counter()-t0
            df=pd.DataFrame(res['data'], columns=res['columns'])
            occ_hash=sha_arr(res['initial_occupancy']); path_hash=sha_arr(res['occupancy_trajectory'])
            n_holes=int(graph.n_sites - np.sum(res['initial_occupancy']))
            df['stage']='stage5c2eR'; df['block']='primary'; df['shape']='x'.join(map(str,shape)); df['N']=int(graph.n_sites); df['label']=label; df['occupancy_idx']=oi; df['path_idx']=pj; df['phase_idx']=pk; df['occupancy_seed']=occupancy_seed; df['hole_path_seed']=path_seed; df['phase_batch_seed']=phase_batch_seed; df['occupancy_hash']=occ_hash; df['path_hash']=path_hash; df['n_holes']=n_holes; df['run_id']=run_id; df['stage5c2eR_source']='new_primary_extension'
            curves.append(df)
            best_i=int(np.nanargmin(df['xi2_db'].to_numpy(float))); fixed=df.iloc[fixed_idx]; best=df.iloc[best_i]
            finals.append({'stage':'stage5c2eR','block':'primary','shape':'x'.join(map(str,shape)),'N':int(graph.n_sites),'label':label,'occupancy_idx':oi,'path_idx':pj,'phase_idx':pk,'occupancy_seed':occupancy_seed,'hole_path_seed':path_seed,'phase_batch_seed':phase_batch_seed,'occupancy_hash':occ_hash,'path_hash':path_hash,'n_holes':n_holes,'run_id':run_id,'xi2_db_fixed':float(fixed['xi2_db']),'xi2_db_min':float(best['xi2_db']),'fixed_time':fixed_time,'time_at_min':float(best['time']),'N_eff_fixed':float(fixed['N_eff']),'active_bonds_fixed':float(fixed['active_bonds']),'runtime_seconds':elapsed,'stage5c2eR_source':'new_primary_extension'})
            registry.append({'block':'primary','occupancy_idx':oi,'path_idx':pj,'phase_idx':pk,'label':label,'occupancy_seed':occupancy_seed,'hole_path_seed':path_seed,'phase_batch_seed':phase_batch_seed,'occupancy_hash':occ_hash,'path_hash':path_hash,'n_holes':n_holes,'run_id':run_id,'stage5c2eR_source':'new_primary_extension'})
    new_curves = pd.concat(curves, ignore_index=True) if curves else pd.DataFrame()
    new_finals = pd.DataFrame(finals)
    new_registry = pd.DataFrame(registry)
    combined_curves = pd.concat([old_curves, new_curves], ignore_index=True)
    combined_finals = pd.concat([old_finals, new_finals], ignore_index=True)
    combined_registry = pd.concat([old_registry, new_registry], ignore_index=True)
    save_dataframe(out/'stage5c2eR_curves_all.csv', combined_curves, raw)
    save_dataframe(out/'stage5c2eR_finals.csv', combined_finals, raw)
    save_dataframe(out/'stage5c2eR_seed_registry.csv', combined_registry, raw)
    save_dataframe(out/'stage5c2eR_new_cells_finals.csv', new_finals, raw)
    save_json(out/'stage5c2eR_primary_manifest.json', {'stage':'stage5c2eR_primary_extension','config':a.config,'config_hash':hash_dict(raw),'existing_primary':str(existing),'shape':list(shape),'target_design':{'occupancies':n_occ,'paths_per_occupancy':n_path,'phase_batches_per_path':n_phase},'new_cells':len(cells),'new_simulator_runs':len(cells)*len(labels),'n_traj':n_traj,'claim_scope':st.get('claim_scope','')})
    print(f'Stage 5C.2E-R primary extension wrote {out}; combined finals={len(combined_finals)} new finals={len(new_finals)}')

if __name__ == '__main__': main()
