#!/usr/bin/env python
from __future__ import annotations
import argparse, sys, math, json, time
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'scripts'))
from stage2_common import load_raw_config
from haxs.io.result_store import ensure_dir, save_dataframe, save_json
from haxs.lattice.graphs import hypercubic_lattice
from haxs.methods.dtwa import run_dtwa
from haxs.models.controls import ControlProtocol

LABEL_OVERRIDES = {
    'static_only': {'hole_fraction': None, 'mobile_eta': 0.0, 'lambda_sd': 0.0, 'control':'off'},
    'mobile_only': {'hole_fraction': None, 'mobile_eta': None, 'lambda_sd': 0.0, 'control':'off'},
    'spin_density_only': {'hole_fraction': None, 'mobile_eta': 0.0, 'lambda_sd': None, 'control':'off'},
    'mobile_plus_spin_density': {'hole_fraction': None, 'mobile_eta': None, 'lambda_sd': None, 'control':'off'},
    'everything': {'hole_fraction': None, 'mobile_eta': None, 'lambda_sd': None, 'control':'everything'},
}

def ctrl(kind:str, jz:float, t_final:float)->ControlProtocol:
    if kind=='off':
        return ControlProtocol(enabled=False,jz_initial=jz,final_time=t_final)
    return ControlProtocol(enabled=True, echo_times=(0.5*t_final,), gradient=0.12, jz_initial=jz, jz_final=0.15, ramp_duration=0.35*t_final, final_time=t_final)

def holm(pvals):
    p=np.asarray(pvals,dtype=float); m=len(p); order=np.argsort(p); adj=np.empty(m); running=0.0
    for rank, idx in enumerate(order, start=1):
        val=(m-rank+1)*p[idx]; running=max(running,val); adj[idx]=min(running,1.0)
    return adj

def boot_ci(arr, seed=1729, n_boot=1500, ci=0.95):
    x=np.asarray(arr,dtype=float); x=x[np.isfinite(x)]
    if len(x)==0: return float('nan'), float('nan')
    rng=np.random.default_rng(seed)
    boots=np.array([rng.choice(x,size=len(x),replace=True).mean() for _ in range(int(n_boot))])
    a=(1-ci)/2
    return float(np.quantile(boots,a)), float(np.quantile(boots,1-a))

def label_params(label, base):
    ov=LABEL_OVERRIDES[label]
    return {
        'hole_fraction': float(base.get('hole_fraction',0.18) if ov['hole_fraction'] is None else ov['hole_fraction']),
        'mobile_eta': float(base.get('mobile_eta',0.55) if ov['mobile_eta'] is None else ov['mobile_eta']),
        'lambda_sd': float(base.get('lambda_sd',0.30) if ov['lambda_sd'] is None else ov['lambda_sd']),
        'control': ov['control'],
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--config',default='configs/stage3b_lite/paired_finite_size.yaml')
    ap.add_argument('--out',default='results/stage3b_lite/paired_finite_size')
    args=ap.parse_args()
    raw=load_raw_config(args.config); out=ensure_dir(ROOT/args.out)
    st=raw.get('stage3b',{})
    seeds=list(range(int(st.get('seed_start',41001)), int(st.get('seed_start',41001))+int(st.get('seeds',18))))
    shapes=st.get('shapes',[[2,3],[3,3],[2,2,2],[3,3,2],[3,3,3]])
    labels=st.get('labels',list(LABEL_OVERRIDES))
    model=raw.get('model',{}); dtwa=raw.get('dtwa',{})
    times=np.linspace(0.0,float(dtwa.get('t_max',1.4)),int(dtwa.get('n_steps',31)))
    fixed_idx=int(round(float(st.get('fixed_time_fraction',0.65))*(len(times)-1)))
    fixed_idx=max(0,min(fixed_idx,len(times)-1))
    fixed_time=float(times[fixed_idx])
    all_curves=[]; finals=[]
    for shape in shapes:
        g=hypercubic_lattice(tuple(shape), raw.get('lattice',{}).get('periodic',False))
        shape_s='x'.join(map(str,shape))
        for label in labels:
            lp=label_params(label,model)
            c=ctrl(lp['control'],float(model.get('jz',0.35)),float(times[-1]))
            for seed in seeds:
                t0=time.perf_counter()
                res=run_dtwa(g,times,j_perp=float(model.get('j_perp',1.0)),jz=float(model.get('jz',0.35)),hole_fraction=lp['hole_fraction'],mobile_eta=lp['mobile_eta'],lambda_sd=lp['lambda_sd'],n_traj=int(dtwa.get('n_traj',64)),seed=int(seed),control=c)
                elapsed=time.perf_counter()-t0
                df=pd.DataFrame(res['data'],columns=res['columns'])
                df['shape']=shape_s; df['dimension']=len(shape); df['N']=int(g.n_sites); df['label']=label; df['seed']=int(seed); df['runtime_seconds']=elapsed; df['fixed_eval_time']=fixed_time
                all_curves.append(df)
                j=int(np.nanargmin(df['xi2_db'].to_numpy(float)))
                fixed=df.iloc[fixed_idx]
                best=df.iloc[j]
                finals.append({'shape':shape_s,'dimension':len(shape),'N':int(g.n_sites),'label':label,'seed':int(seed),'xi2_db_min':float(best['xi2_db']),'time_at_min':float(best['time']),'xi2_db_fixed':float(fixed['xi2_db']),'fixed_time':fixed_time,'spin_length_min':float(best['spin_length']),'spin_length_fixed':float(fixed['spin_length']),'N_eff_min':float(best['N_eff']),'active_bonds_min':float(best['active_bonds']),'runtime_seconds':elapsed})
    curves=pd.concat(all_curves,ignore_index=True)
    finals_df=pd.DataFrame(finals)
    # paired shape-level core and supporting pairs
    core_a,core_b=st.get('core_pair',['static_only','mobile_plus_spin_density'])
    pair_defs=[(core_a,core_b),('mobile_plus_spin_density','everything'),('static_only','everything')]
    rows=[]; pvals=[]
    for shape_s,g in finals_df.groupby('shape'):
        dim=int(g['dimension'].iloc[0]); N=int(g['N'].iloc[0])
        for metric in ['xi2_db_min','xi2_db_fixed']:
            for a,b in pair_defs:
                pa=g[g.label==a][['seed',metric]].rename(columns={metric:'a'})
                pb=g[g.label==b][['seed',metric]].rename(columns={metric:'b'})
                m=pa.merge(pb,on='seed')
                if len(m)<2: continue
                d=(m['a']-m['b']).to_numpy(float)
                lo,hi=boot_ci(d,seed=int(raw.get('seed',1729))+N+n_boot_offset(metric),n_boot=int(st.get('bootstrap_samples',1500)),ci=float(st.get('ci',0.95)))
                tt=stats.ttest_1samp(d,0.0,nan_policy='omit')
                sd=float(np.std(d,ddof=1)); dz=float(np.mean(d)/sd) if sd>0 else float('nan')
                rows.append({'shape':shape_s,'dimension':dim,'N':N,'metric':metric,'group_a':a,'group_b':b,'n_pairs':len(d),'paired_mean_difference_a_minus_b':float(np.mean(d)),'bootstrap_ci_low':lo,'bootstrap_ci_high':hi,'paired_t_p':float(tt.pvalue),'cohens_dz':dz,'ci_excludes_zero':not(lo<=0<=hi),'pre_registered_core': bool(a==core_a and b==core_b),'direction_note':'negative means group_a has stronger squeezing because xi2_db is lower'})
                pvals.append(float(tt.pvalue))
    pair_df=pd.DataFrame(rows)
    if len(pair_df):
        pair_df['holm_paired_t_p']=holm(pair_df['paired_t_p'].to_numpy(float))
        pair_df['holm_significant_0p05']=pair_df['holm_paired_t_p']<0.05
    core=pair_df[(pair_df.pre_registered_core)&(pair_df.metric=='xi2_db_min')].copy()
    dim_rows=[]
    if len(core):
        for dim,g in core.groupby('dimension'):
            diffs=g['paired_mean_difference_a_minus_b'].to_numpy(float)
            dim_rows.append({'dimension':int(dim),'n_shapes':int(len(g)),'mean_shape_effect_db':float(np.mean(diffs)),'all_shapes_negative':bool(np.all(diffs<0)),'shapes_ci_excluding_zero':int(g['ci_excludes_zero'].sum())})
    dim_df=pd.DataFrame(dim_rows)
    save_dataframe(out/'stage3b_curves_all.csv',curves,raw)
    save_dataframe(out/'stage3b_finals.csv',finals_df,raw)
    save_dataframe(out/'stage3b_paired_shape_effects.csv',pair_df,raw)
    save_dataframe(out/'stage3b_dimension_summary.csv',dim_df,raw)
    core_pass_shapes=int(((core['paired_mean_difference_a_minus_b']<0)&(core['ci_excludes_zero'])).sum()) if len(core) else 0
    neg_shapes=int((core['paired_mean_difference_a_minus_b']<0).sum()) if len(core) else 0
    pass_gate=bool(core_pass_shapes>=int(st.get('pass_min_shapes',4)) and dim_df.get('all_shapes_negative',pd.Series(dtype=bool)).sum()>=int(st.get('pass_min_dimension_families',2)))
    save_json(out/'stage3b_paired_finite_size_manifest.json',{'stage':'stage3b','config':args.config,'shapes':shapes,'labels':labels,'seeds':len(seeds),'n_traj':int(dtwa.get('n_traj',64)),'fixed_time':fixed_time,'core_pair':[core_a,core_b],'core_negative_shapes':neg_shapes,'core_passing_shapes':core_pass_shapes,'passed':pass_gate})
    print(f'stage3b paired finite-size wrote {out}; shapes={len(shapes)} labels={len(labels)} seeds={len(seeds)} core_passing_shapes={core_pass_shapes} passed={pass_gate}')

def n_boot_offset(metric):
    return 0 if metric=='xi2_db_min' else 7919
if __name__=='__main__': main()
