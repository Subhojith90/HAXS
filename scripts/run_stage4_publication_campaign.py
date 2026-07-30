#!/usr/bin/env python
from __future__ import annotations
import argparse, sys, time
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src')); sys.path.insert(0,str(ROOT/'scripts'))
from stage2_common import load_raw_config
from haxs.io.result_store import ensure_dir, save_dataframe, save_json
from haxs.lattice.graphs import hypercubic_lattice
from haxs.methods.dtwa import run_dtwa
from haxs.models.controls import ControlProtocol
LABEL_OVERRIDES={
 'static_only':{'hole_fraction':None,'mobile_eta':0.0,'lambda_sd':0.0,'control':'off'},
 'mobile_only':{'hole_fraction':None,'mobile_eta':None,'lambda_sd':0.0,'control':'off'},
 'spin_density_only':{'hole_fraction':None,'mobile_eta':0.0,'lambda_sd':None,'control':'off'},
 'mobile_plus_spin_density':{'hole_fraction':None,'mobile_eta':None,'lambda_sd':None,'control':'off'},
 'everything':{'hole_fraction':None,'mobile_eta':None,'lambda_sd':None,'control':'everything'},
 'full_controlled':{'hole_fraction':None,'mobile_eta':None,'lambda_sd':None,'control':'everything'},
}
def ctrl(kind,jz,t_final):
    if kind=='off': return ControlProtocol(enabled=False,jz_initial=jz,final_time=t_final)
    return ControlProtocol(enabled=True,echo_times=(0.5*t_final,),gradient=0.12,jz_initial=jz,jz_final=0.15,ramp_duration=0.35*t_final,final_time=t_final)
def label_params(label,base):
    ov=LABEL_OVERRIDES[label]
    return dict(hole_fraction=float(base.get('hole_fraction',0.18) if ov['hole_fraction'] is None else ov['hole_fraction']), mobile_eta=float(base.get('mobile_eta',0.55) if ov['mobile_eta'] is None else ov['mobile_eta']), lambda_sd=float(base.get('lambda_sd',0.30) if ov['lambda_sd'] is None else ov['lambda_sd']), control=ov['control'])
def boot_ci(x,seed=1729,n_boot=1000,ci=0.95):
    arr=np.asarray(x,dtype=float); arr=arr[np.isfinite(arr)]
    if len(arr)==0: return np.nan,np.nan
    rng=np.random.default_rng(seed); boots=[rng.choice(arr,size=len(arr),replace=True).mean() for _ in range(int(n_boot))]
    a=(1-ci)/2; return float(np.quantile(boots,a)),float(np.quantile(boots,1-a))
def holm(pvals):
    p=np.asarray(pvals,float); m=len(p); order=np.argsort(p); adj=np.empty(m); running=0.0
    for rank,idx in enumerate(order,1):
        running=max(running,(m-rank+1)*p[idx]); adj[idx]=min(running,1.0)
    return adj
def family_shapes(st):
    rows=[]
    for fam in st.get('matched_families',[]):
        for sh in fam.get('shapes',[]): rows.append((fam.get('family','unlabeled'),'x'.join(map(str,sh)),sh))
    return rows
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--config',default='configs/stage4_lite/publication_campaign.yaml'); ap.add_argument('--out',default='results/stage4_lite/publication_campaign')
    args=ap.parse_args(); raw=load_raw_config(args.config); out=ensure_dir(ROOT/args.out)
    st=raw.get('stage4',{}); model=raw.get('model',{}); dtwa=raw.get('dtwa',{})
    seeds=list(range(int(st.get('seed_start',61001)),int(st.get('seed_start',61001))+int(st.get('seeds',8))))
    reps=int(st.get('trajectory_reps',2)); stride=int(st.get('trajectory_seed_stride',100000)); seed_offset=int(st.get('trajectory_seed_offset',0))
    labels=st.get('labels',['static_only','mobile_plus_spin_density','everything'])
    times=np.linspace(0,float(dtwa.get('t_max',1.4)),int(dtwa.get('n_steps',31)))
    fixed_idx=max(0,min(len(times)-1,int(round(float(st.get('fixed_time_fraction',0.65))*(len(times)-1))))); fixed_time=float(times[fixed_idx])
    curves=[]; finals=[]
    for family,shape_s,shape in family_shapes(st):
        g=hypercubic_lattice(tuple(shape),raw.get('lattice',{}).get('periodic',False))
        for label in labels:
            lp=label_params(label,model); c=ctrl(lp['control'],float(model.get('jz',0.35)),float(times[-1]))
            for seed in seeds:
                for rep in range(reps):
                    run_seed=int(seed)+seed_offset+rep*stride
                    t0=time.perf_counter(); res=run_dtwa(g,times,j_perp=float(model.get('j_perp',1.0)),jz=float(model.get('jz',0.35)),hole_fraction=lp['hole_fraction'],mobile_eta=lp['mobile_eta'],lambda_sd=lp['lambda_sd'],n_traj=int(dtwa.get('n_traj',48)),seed=run_seed,control=c); elapsed=time.perf_counter()-t0
                    df=pd.DataFrame(res['data'],columns=res['columns']); df['family']=family; df['shape']=shape_s; df['dimension']=len(shape); df['N']=int(g.n_sites); df['label']=label; df['disorder_seed']=int(seed); df['trajectory_rep']=int(rep); df['run_seed']=run_seed
                    curves.append(df)
                    j=int(np.nanargmin(df['xi2_db'].to_numpy(float))); best=df.iloc[j]; fixed=df.iloc[fixed_idx]
                    finals.append({'family':family,'shape':shape_s,'dimension':len(shape),'N':int(g.n_sites),'label':label,'disorder_seed':int(seed),'trajectory_rep':int(rep),'run_seed':run_seed,'xi2_db_fixed':float(fixed['xi2_db']),'xi2_db_min':float(best['xi2_db']),'fixed_time':fixed_time,'time_at_min':float(best['time']),'spin_length_fixed':float(fixed['spin_length']),'spin_length_min':float(best['spin_length']),'runtime_seconds':elapsed})
    curves_df=pd.concat(curves,ignore_index=True); finals_df=pd.DataFrame(finals)
    seed_avg=finals_df.groupby(['family','shape','dimension','N','label','disorder_seed'],as_index=False)[['xi2_db_fixed','xi2_db_min','spin_length_fixed','spin_length_min']].mean()
    a,b=st.get('primary_pair',['static_only','mobile_plus_spin_density']); pair_rows=[]
    for metric in ['xi2_db_fixed','xi2_db_min']:
        for shape_s,g in seed_avg.groupby('shape'):
            pa=g[g.label==a][['disorder_seed',metric]].rename(columns={metric:'a'}); pb=g[g.label==b][['disorder_seed',metric]].rename(columns={metric:'b'})
            m=pa.merge(pb,on='disorder_seed'); d=(m.a-m.b).to_numpy(float)
            if len(d)<2: continue
            lo,hi=boot_ci(d,seed=int(raw.get('seed',1729))+len(shape_s)+(0 if metric.endswith('fixed') else 1009),n_boot=int(st.get('bootstrap_samples',1000)),ci=float(st.get('ci',0.95)))
            tt=stats.ttest_1samp(d,0.0,nan_policy='omit'); sd=float(np.std(d,ddof=1)); dz=float(np.mean(d)/sd) if sd>0 else np.nan
            pair_rows.append({'family':str(g.family.iloc[0]),'shape':shape_s,'dimension':int(g.dimension.iloc[0]),'N':int(g.N.iloc[0]),'metric':metric,'group_a':a,'group_b':b,'n_disorder_pairs':len(d),'trajectory_reps_per_seed':reps,'mean_effect_db':float(np.mean(d)),'bootstrap_ci_low':lo,'bootstrap_ci_high':hi,'paired_t_p':float(tt.pvalue),'cohens_dz':dz,'ci_excludes_zero':not(lo<=0<=hi),'primary_fixed_time':metric=='xi2_db_fixed'})
    pair_df=pd.DataFrame(pair_rows)
    if len(pair_df): pair_df['holm_paired_t_p']=holm(pair_df.paired_t_p.to_numpy(float)); pair_df['holm_significant_0p05']=pair_df.holm_paired_t_p<0.05
    nested=[]
    for shape_s,g in finals_df.groupby('shape'):
        for metric in ['xi2_db_fixed','xi2_db_min']:
            pa=g[g.label==a][['disorder_seed','trajectory_rep',metric]].rename(columns={metric:'a'}); pb=g[g.label==b][['disorder_seed','trajectory_rep',metric]].rename(columns={metric:'b'})
            m=pa.merge(pb,on=['disorder_seed','trajectory_rep'])
            if len(m)==0: continue
            m['diff']=m.a-m.b; by=m.groupby('disorder_seed')['diff']; means=by.mean().to_numpy(float)
            within=float(by.var(ddof=1).fillna(0).mean()); between=float(np.var(means,ddof=1)) if len(means)>1 else 0.0; total=between+within/max(reps,1); se=(total/max(len(means),1))**0.5 if total>=0 else np.nan
            nested.append({'family':str(g.family.iloc[0]),'shape':shape_s,'dimension':int(g.dimension.iloc[0]),'N':int(g.N.iloc[0]),'metric':metric,'mean_effect_db':float(np.mean(means)),'nested_standard_error':float(se),'between_disorder_variance':between,'mean_within_trajectory_variance':within,'trajectory_fraction_of_total_variance':float((within/max(reps,1))/(total if total>0 else np.nan)),'nested_effect_stable': bool(np.mean(means)<0 and abs(np.mean(means))>1.96*se)})
    nested_df=pd.DataFrame(nested)
    primary=pair_df[pair_df.metric=='xi2_db_fixed'] if len(pair_df) else pd.DataFrame(); fam_rows=[]
    if len(primary):
        for fam,g in primary.groupby('family'):
            fam_rows.append({'family':fam,'n_shapes':int(len(g)),'mean_fixed_effect_db':float(g.mean_effect_db.mean()),'all_fixed_negative':bool((g.mean_effect_db<0).all()),'fixed_ci_shapes':int(g.ci_excludes_zero.sum())})
    fam_df=pd.DataFrame(fam_rows)
    save_dataframe(out/'stage4_curves_all.csv',curves_df,raw); save_dataframe(out/'stage4_finals.csv',finals_df,raw); save_dataframe(out/'stage4_seed_averaged_finals.csv',seed_avg,raw); save_dataframe(out/'stage4_primary_pair_effects.csv',pair_df,raw); save_dataframe(out/'stage4_nested_uncertainty.csv',nested_df,raw); save_dataframe(out/'stage4_family_summary.csv',fam_df,raw)
    gates=st.get('gates',{}); neg=int((primary.mean_effect_db<0).sum()) if len(primary) else 0; ci=int(primary.ci_excludes_zero.sum()) if len(primary) else 0; stable=int(nested_df[(nested_df.metric=='xi2_db_fixed')].nested_effect_stable.sum()) if len(nested_df) else 0
    passed=bool(neg>=int(gates.get('min_fixed_negative_shapes',3)) and ci>=int(gates.get('min_fixed_ci_shapes',2)) and stable>=int(gates.get('min_nested_stable_shapes',2)))
    save_json(out/'stage4_publication_campaign_manifest.json',{'stage':'stage4_publication_mechanism_campaign','config':args.config,'passed':passed,'fixed_time':fixed_time,'primary_pair':[a,b],'shapes':[x[2] for x in family_shapes(st)],'labels':labels,'seeds':len(seeds),'trajectory_reps':reps,'n_traj':int(dtwa.get('n_traj',48)),'fixed_negative_shapes':neg,'fixed_ci_excluding_zero_shapes':ci,'nested_stable_shapes':stable,'claim_scope':'mechanism surrogate only; no constructive recovery/no-go/exact mobile-hole claim'})
    print(f'stage4 publication campaign wrote {out}; passed={passed}; fixed_negative_shapes={neg}; fixed_ci_shapes={ci}; nested_stable_shapes={stable}')
if __name__=='__main__': main()
