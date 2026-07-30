#!/usr/bin/env python
from __future__ import annotations
import argparse, sys, math
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src')); sys.path.insert(0,str(ROOT/'scripts'))
from stage2_common import load_raw_config
from haxs.io.result_store import ensure_dir, save_dataframe, save_json

def z_for_power(power: float) -> float:
    return float(stats.norm.ppf(power))

def classify(effect, ci_excludes, traj_frac, projected_n, current_n, floor, cap):
    labels=[]
    if not np.isfinite(effect) or abs(effect) < floor: labels.append('weak_effect')
    if np.isfinite(traj_frac) and traj_frac > 0.50: labels.append('trajectory_dominated')
    if np.isfinite(projected_n) and projected_n > max(current_n,1): labels.append('underpowered')
    if effect < -floor and projected_n <= cap: labels.append('promising')
    if ci_excludes: labels.append('ci_excludes_zero')
    return ';'.join(labels) if labels else 'inconclusive'

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--config',default='configs/stage4a_lite/stability_diagnosis.yaml')
    ap.add_argument('--campaign-dir',default='results/stage4a_lite/publication_campaign')
    ap.add_argument('--out',default='results/stage4a_lite/stability_diagnosis')
    args=ap.parse_args()
    raw=load_raw_config(args.config); st=raw.get('stage4',{}); s4a=raw.get('stage4a',{})
    cdir=ROOT/args.campaign_dir; out=ensure_dir(ROOT/args.out)
    pair=pd.read_csv(cdir/'stage4_primary_pair_effects.csv')
    nested=pd.read_csv(cdir/'stage4_nested_uncertainty.csv')
    fam=pd.read_csv(cdir/'stage4_family_summary.csv') if (cdir/'stage4_family_summary.csv').exists() else pd.DataFrame()
    final=pd.read_csv(cdir/'stage4_finals.csv')
    floor=float(s4a.get('effect_floor_db',0.2)); power=float(s4a.get('target_power',0.8)); alpha=float(s4a.get('alpha',0.05)); cap=int(s4a.get('max_recommended_seed_cap',500))
    zcrit=float(stats.norm.ppf(1-alpha/2)); zpow=z_for_power(power)
    # Shape-level power/stability diagnosis for fixed-time primary metric
    primary=pair[pair.metric=='xi2_db_fixed'].copy()
    rows=[]
    for _,r in primary.iterrows():
        nshape=nested[(nested['shape']==r['shape']) & (nested.metric=='xi2_db_fixed')]
        traj_frac=float(nshape.trajectory_fraction_of_total_variance.iloc[0]) if len(nshape) else np.nan
        se=float(nshape.nested_standard_error.iloc[0]) if len(nshape) else np.nan
        current_n=int(r.get('n_disorder_pairs', st.get('seeds',np.nan)))
        effect=float(r.mean_effect_db)
        sigma=se*math.sqrt(current_n) if np.isfinite(se) else np.nan
        req_n=float(((zcrit+zpow)*sigma/max(abs(effect),1e-12))**2) if np.isfinite(sigma) else np.nan
        req_n_ceil=int(math.ceil(req_n)) if np.isfinite(req_n) and req_n<1e7 else -1
        rows.append({
            'family':r['family'],'shape':r['shape'],'dimension':int(r['dimension']),'N':int(r['N']),
            'current_disorder_pairs':current_n,'trajectory_reps_per_seed':int(r.trajectory_reps_per_seed),
            'fixed_time_mean_effect_db':effect,'fixed_time_ci_low':float(r.bootstrap_ci_low),'fixed_time_ci_high':float(r.bootstrap_ci_high),
            'fixed_time_ci_excludes_zero':bool(r.ci_excludes_zero),'nested_standard_error':se,
            'trajectory_fraction_of_total_variance':traj_frac,'projected_disorder_pairs_for_80pct_power':req_n_ceil,
            'diagnosis':classify(effect,bool(r.ci_excludes_zero),traj_frac,req_n_ceil,current_n,floor,cap)
        })
    diag=pd.DataFrame(rows)
    # Metric sensitivity: min-time vs fixed-time per shape
    sens=[]
    for shape,g in pair.groupby('shape'):
        fixed=g[g.metric=='xi2_db_fixed']; mint=g[g.metric=='xi2_db_min']
        if len(fixed) and len(mint):
            sens.append({'shape':shape,'dimension':int(fixed.dimension.iloc[0]),'N':int(fixed.N.iloc[0]),
                         'fixed_effect_db':float(fixed.mean_effect_db.iloc[0]),'min_effect_db':float(mint.mean_effect_db.iloc[0]),
                         'min_minus_fixed_effect_db':float(mint.mean_effect_db.iloc[0]-fixed.mean_effect_db.iloc[0]),
                         'fixed_ci_excludes_zero':bool(fixed.ci_excludes_zero.iloc[0]),'min_ci_excludes_zero':bool(mint.ci_excludes_zero.iloc[0])})
    sens_df=pd.DataFrame(sens)
    # Variance decomposition summary
    var_df=nested.copy()
    var_df['dominant_uncertainty_source']=np.where(var_df.trajectory_fraction_of_total_variance>0.5,'trajectory','disorder')
    # Leave-one-shape-out stability on fixed-time effects
    loo=[]
    eff=diag['fixed_time_mean_effect_db'].to_numpy(float) if len(diag) else np.array([])
    shapes=diag['shape'].tolist() if len(diag) else []
    for i,sh in enumerate(shapes):
        rem=np.delete(eff,i)
        loo.append({'left_out_shape':sh,'mean_fixed_effect_without_shape':float(np.mean(rem)) if len(rem) else np.nan,'all_remaining_negative':bool((rem<0).all()) if len(rem) else False})
    loo_df=pd.DataFrame(loo)
    # Decision stats
    fixed_negative=int((diag.fixed_time_mean_effect_db<0).sum()) if len(diag) else 0
    fixed_ci=int(diag.fixed_time_ci_excludes_zero.sum()) if len(diag) else 0
    promising=int(diag.diagnosis.str.contains('promising').sum()) if len(diag) else 0
    traj_dom=int(diag.diagnosis.str.contains('trajectory_dominated').sum()) if len(diag) else 0
    median_req=float(diag.loc[diag.projected_disorder_pairs_for_80pct_power>0,'projected_disorder_pairs_for_80pct_power'].median()) if len(diag) and (diag.projected_disorder_pairs_for_80pct_power>0).any() else np.nan
    save_dataframe(out/'stage4a_shape_stability_diagnosis.csv',diag,raw)
    save_dataframe(out/'stage4a_metric_sensitivity.csv',sens_df,raw)
    save_dataframe(out/'stage4a_variance_decomposition.csv',var_df,raw)
    save_dataframe(out/'stage4a_leave_one_shape_out.csv',loo_df,raw)
    save_json(out/'stage4a_stability_manifest.json',{
        'stage':'stage4a_mechanism_stability_diagnosis','config':args.config,'campaign_dir':args.campaign_dir,
        'fixed_negative_shapes':fixed_negative,'fixed_ci_shapes':fixed_ci,'promising_shapes':promising,
        'trajectory_dominated_shapes':traj_dom,'median_projected_disorder_pairs_for_80pct_power':median_req,
        'diagnosis_route':'stage4a_diagnosis_complete_targeted_stage4b_design_needed',
        'interpretation':'diagnostic package; does not authorize publication claims by itself'
    })
    print(f'stage4a stability diagnosis wrote {out}; fixed_negative_shapes={fixed_negative}; fixed_ci_shapes={fixed_ci}; promising_shapes={promising}; median_projected_n={median_req}')
if __name__=='__main__': main()
