#!/usr/bin/env python
from __future__ import annotations
import argparse, subprocess, sys, math
from pathlib import Path
import numpy as np, pandas as pd, yaml
from scipy import stats
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from haxs.io.result_store import ensure_dir, save_dataframe, save_json

def run(cmd):
    print('RUN:', ' '.join(map(str,cmd)), flush=True)
    subprocess.run([str(x) for x in cmd], cwd=ROOT, check=True)

def t_ci(x, alpha=0.05):
    arr=np.asarray(x,dtype=float); arr=arr[np.isfinite(arr)]
    if len(arr)<2:
        return float('nan'),float('nan'),float('nan')
    mean=float(arr.mean()); se=float(arr.std(ddof=1)/math.sqrt(len(arr)))
    q=float(stats.t.ppf(1-alpha/2, df=len(arr)-1))
    p=float(stats.ttest_1samp(arr,0.0,nan_policy='omit').pvalue)
    return mean-q*se, mean+q*se, p

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--config',default='configs/stage4d_lite/targeted_publication_pilot.yaml')
    ap.add_argument('--out',default='results/stage4d_lite')
    args=ap.parse_args()
    raw=yaml.safe_load((ROOT/args.config).read_text())
    out=ensure_dir(ROOT/args.out)
    camp=out/'publication_pilot'
    diag=out/'stability_diagnosis'
    run([sys.executable,'scripts/run_stage4_publication_campaign.py','--config',args.config,'--out',str(camp.relative_to(ROOT))])
    run([sys.executable,'scripts/run_stage4a_stability_diagnosis.py','--config',args.config,'--campaign-dir',str(camp.relative_to(ROOT)),'--out',str(diag.relative_to(ROOT))])
    final=pd.read_csv(camp/'stage4_finals.csv')
    pair=pd.read_csv(camp/'stage4_primary_pair_effects.csv')
    nested=pd.read_csv(camp/'stage4_nested_uncertainty.csv')
    seed_avg=pd.read_csv(camp/'stage4_seed_averaged_finals.csv')
    a,b=raw['stage4']['primary_pair']
    stage4d=raw.get('stage4d',{})
    alpha=1-float(raw['stage4'].get('ci',0.95))
    rows=[]
    for metric in ['xi2_db_fixed','xi2_db_min']:
        for shape,g in seed_avg.groupby('shape'):
            pa=g[g.label==a][['disorder_seed',metric]].rename(columns={metric:'a'})
            pb=g[g.label==b][['disorder_seed',metric]].rename(columns={metric:'b'})
            m=pa.merge(pb,on='disorder_seed'); d=(m.a-m.b).to_numpy(float)
            lo,hi,p=t_ci(d,alpha=alpha)
            sign_count=int((d<0).sum())
            n=len(d)
            mean=float(np.mean(d)) if n else float('nan')
            sd=float(np.std(d,ddof=1)) if n>1 else float('nan')
            dz=float(mean/sd) if sd and sd>0 else float('nan')
            # Conservative sample projection using t-style normal approximation.
            target_power=0.80; zcrit=stats.norm.ppf(1-alpha/2); zpow=stats.norm.ppf(target_power)
            req=int(math.ceil(((zcrit+zpow)*sd/max(abs(mean),1e-12))**2)) if np.isfinite(sd) and abs(mean)>1e-12 else -1
            rows.append({'shape':shape,'metric':metric,'n_disorder_pairs':n,'mean_effect_db':mean,'t_ci_low':lo,'t_ci_high':hi,'t_ci_excludes_zero':bool(np.isfinite(lo) and not (lo<=0<=hi)),'paired_t_p':p,'negative_seed_count':sign_count,'positive_or_zero_seed_count':int(n-sign_count),'cohens_dz':dz,'projected_pairs_for_80pct_power':req})
    tdf=pd.DataFrame(rows)
    primary=pair[pair.metric=='xi2_db_fixed'].copy()
    nested_fixed=nested[nested.metric=='xi2_db_fixed'].copy()
    tprimary=tdf[tdf.metric=='xi2_db_fixed'].copy()
    merged=primary.merge(tprimary[['shape','t_ci_low','t_ci_high','t_ci_excludes_zero','negative_seed_count','projected_pairs_for_80pct_power']],on='shape',how='left')
    merged=merged.merge(nested_fixed[['shape','nested_standard_error','trajectory_fraction_of_total_variance','nested_effect_stable']],on='shape',how='left')
    merged['trajectory_dominated']=merged['trajectory_fraction_of_total_variance']>float(stage4d.get('trajectory_fraction_threshold',0.5))
    merged['publication_pilot_pass_shape']=((merged['mean_effect_db']<0) & (merged['t_ci_excludes_zero'] | merged['ci_excludes_zero']) & (~merged['trajectory_dominated']))
    required_shapes=set(map(str,stage4d.get('required_shapes',[])))
    shape_set=set(map(str,merged['shape'].tolist()))
    shape_gate=required_shapes.issubset(shape_set) if required_shapes else True
    fixed_negative=int((merged.mean_effect_db<0).sum())
    bootstrap_ci=int(merged.ci_excludes_zero.sum())
    t_ci_count=int(merged.t_ci_excludes_zero.sum())
    traj_dom=int(merged.trajectory_dominated.sum())
    shape_pass=int(merged.publication_pilot_pass_shape.sum())
    ready=bool(shape_gate and fixed_negative>=int(stage4d.get('required_fixed_negative_shapes',2)) and bootstrap_ci>=int(stage4d.get('required_bootstrap_ci_shapes',1)) and t_ci_count>=int(stage4d.get('required_t_ci_shapes',1)) and traj_dom<=int(raw['stage4']['gates'].get('max_trajectory_dominated_shapes',1)))
    if ready:
        route='stage4d_pilot_passed_prepare_stage5_design_review'
    elif fixed_negative>=1 and bootstrap_ci>=1:
        route='stage4d_directional_signal_needs_more_pairs_or_trajectories'
    else:
        route='stage4d_negative_result_reconsider_mechanism_claim'
    rec=[]
    for _,r in merged.iterrows():
        rec.append({'shape':r['shape'],'current_pairs':int(r['n_disorder_pairs']),'current_trajectory_reps':int(r['trajectory_reps_per_seed']),'recommended_next_pairs':max(int(stage4d.get('recommended_next_seed_floor',32)), int(r['projected_pairs_for_80pct_power']) if int(r['projected_pairs_for_80pct_power'])>0 else int(stage4d.get('recommended_next_seed_floor',32))),'recommended_next_ntraj':int(raw['dtwa']['n_traj']),'recommended_next_trajectory_reps':max(int(raw['stage4']['trajectory_reps']),6),'reason':'scale disorder pairs only after trajectory fraction is not dominant' if bool(r['trajectory_dominated']) else 'candidate for targeted scaling'})
    recdf=pd.DataFrame(rec)
    readiness=pd.DataFrame([
        {'gate':'required_shapes_present','value':shape_gate},
        {'gate':'fixed_negative_shapes','value':fixed_negative},
        {'gate':'bootstrap_ci_shapes','value':bootstrap_ci},
        {'gate':'t_ci_shapes','value':t_ci_count},
        {'gate':'trajectory_dominated_shapes','value':traj_dom},
        {'gate':'shape_pass_count','value':shape_pass},
        {'gate':'route','value':route},
    ])
    save_dataframe(out/'stage4d_seed_level_t_intervals.csv',tdf,raw)
    save_dataframe(out/'stage4d_primary_readiness_by_shape.csv',merged,raw)
    save_dataframe(out/'stage4d_recommended_stage5_design.csv',recdf,raw)
    save_dataframe(out/'stage4d_publication_readiness.csv',readiness,raw)
    save_json(out/'stage4d_publication_pilot_manifest.json',{'stage':'stage4d_targeted_publication_pilot','config':args.config,'route':route,'required_shapes_present':shape_gate,'fixed_negative_shapes':fixed_negative,'bootstrap_ci_shapes':bootstrap_ci,'t_ci_shapes':t_ci_count,'trajectory_dominated_shapes':traj_dom,'shape_pass_count':shape_pass,'claim_scope':'targeted publication pilot; supervisor checkpoint, not final publication claim'})
    print(f'stage4d targeted publication pilot wrote {out}; route={route}; fixed_negative={fixed_negative}; t_ci_shapes={t_ci_count}; traj_dom={traj_dom}')
if __name__=='__main__': main()
