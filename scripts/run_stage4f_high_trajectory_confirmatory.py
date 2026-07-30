#!/usr/bin/env python
from __future__ import annotations
import argparse, math, subprocess, sys
from pathlib import Path
import numpy as np, pandas as pd, yaml
from scipy import stats
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from haxs.io.result_store import ensure_dir, save_dataframe, save_json

def run(cmd):
    print('RUN:', ' '.join(map(str,cmd)), flush=True)
    subprocess.run([str(x) for x in cmd], cwd=ROOT, check=True)

def t_interval(vals, ci=0.95):
    x=np.asarray(vals,dtype=float); x=x[np.isfinite(x)]
    if len(x)<2:
        return (float(np.nanmean(x)) if len(x) else np.nan, np.nan, np.nan, np.nan)
    mean=float(x.mean()); se=float(x.std(ddof=1)/math.sqrt(len(x)))
    q=float(stats.t.ppf(0.5+ci/2, df=len(x)-1))
    p=float(stats.ttest_1samp(x,0.0,nan_policy='omit').pvalue)
    return mean, mean-q*se, mean+q*se, p

def load_csv(path):
    return pd.read_csv(path) if Path(path).exists() else pd.DataFrame()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--config', default='configs/stage4f_lite/high_trajectory_confirmatory.yaml')
    ap.add_argument('--out', default='results/stage4f_lite/high_trajectory_confirmatory')
    args=ap.parse_args()
    raw=yaml.safe_load((ROOT/args.config).read_text())
    out=ensure_dir(ROOT/args.out)
    gen=ensure_dir(out/'_generated_configs')
    st4e=raw.get('stage4f',{})
    ntraj_sweep=[int(x) for x in st4e.get('ntraj_sweep',[8,16,32])]
    target_shape=str(st4e.get('target_shape','3x3x2'))
    reps=int(st4e.get('trajectory_reps', raw.get('stage4',{}).get('trajectory_reps',4)))
    seeds=int(st4e.get('seeds', raw.get('stage4',{}).get('seeds',8)))
    ci=float(raw.get('stage4',{}).get('ci',0.95))
    summary=[]; shape_rows=[]; power_rows=[]
    for ntraj in ntraj_sweep:
        cfg=dict(raw)
        cfg['dtwa']=dict(raw.get('dtwa',{})); cfg['dtwa']['n_traj']=int(ntraj)
        cfg['stage4']=dict(raw.get('stage4',{})); cfg['stage4']['trajectory_reps']=reps; cfg['stage4']['seeds']=seeds
        cfg['stage4']['matched_families']=[{'family':st4e.get('target_family','targeted_3d_promising'),'shapes':[[3,3,2]]}]
        cfg_path=gen/f'trajectory_stabilization_ntraj_{ntraj}.yaml'
        cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False))
        camp=out/f'campaign_ntraj_{ntraj}'
        diag=out/f'diagnosis_ntraj_{ntraj}'
        run([sys.executable,'scripts/run_stage4_publication_campaign.py','--config',str(cfg_path.relative_to(ROOT)),'--out',str(camp.relative_to(ROOT))])
        run([sys.executable,'scripts/run_stage4a_stability_diagnosis.py','--config',str(cfg_path.relative_to(ROOT)),'--campaign-dir',str(camp.relative_to(ROOT)),'--out',str(diag.relative_to(ROOT))])
        pair=load_csv(camp/'stage4_primary_pair_effects.csv')
        nested=load_csv(camp/'stage4_nested_uncertainty.csv')
        seed_avg=load_csv(camp/'stage4_seed_averaged_finals.csv')
        manifest=yaml.safe_load((camp/'stage4_publication_campaign_manifest.json').read_text()) if (camp/'stage4_publication_campaign_manifest.json').exists() else {}
        pfix=pair[(pair['shape'].astype(str)==target_shape)&(pair['metric']=='xi2_db_fixed')] if len(pair) else pd.DataFrame()
        nfix=nested[(nested['shape'].astype(str)==target_shape)&(nested['metric']=='xi2_db_fixed')] if len(nested) else pd.DataFrame()
        a,b=raw['stage4']['primary_pair']
        d=np.array([])
        if len(seed_avg):
            pa=seed_avg[(seed_avg.label==a)&(seed_avg['shape'].astype(str)==target_shape)][['disorder_seed','xi2_db_fixed']].rename(columns={'xi2_db_fixed':'a'})
            pb=seed_avg[(seed_avg.label==b)&(seed_avg['shape'].astype(str)==target_shape)][['disorder_seed','xi2_db_fixed']].rename(columns={'xi2_db_fixed':'b'})
            m=pa.merge(pb,on='disorder_seed'); d=(m.a-m.b).to_numpy(float)
        mean,lo,hi,p=t_interval(d,ci=ci)
        neg=int((d<0).sum()) if len(d) else 0
        frac=neg/max(len(d),1)
        sd=float(np.std(d,ddof=1)) if len(d)>1 else np.nan
        zcrit=float(stats.norm.ppf(0.5+ci/2)); zpow=float(stats.norm.ppf(0.80))
        req=int(math.ceil(((zcrit+zpow)*sd/max(abs(mean),1e-12))**2)) if np.isfinite(sd) and abs(mean)>1e-12 else -1
        traj_frac=float(nfix['trajectory_fraction_of_total_variance'].iloc[0]) if len(nfix) else np.nan
        nested_stable=bool(nfix['nested_effect_stable'].iloc[0]) if len(nfix) else False
        boot_lo=float(pfix['bootstrap_ci_low'].iloc[0]) if len(pfix) else np.nan
        boot_hi=float(pfix['bootstrap_ci_high'].iloc[0]) if len(pfix) else np.nan
        boot_excl=bool(pfix['ci_excludes_zero'].iloc[0]) if len(pfix) else False
        row={'n_traj':ntraj,'trajectory_reps':reps,'disorder_seeds':seeds,'shape':target_shape,'mean_fixed_effect_db':mean,'t_ci_low':lo,'t_ci_high':hi,'t_ci_excludes_zero':bool(np.isfinite(lo) and not (lo<=0<=hi)),'paired_t_p':p,'bootstrap_ci_low':boot_lo,'bootstrap_ci_high':boot_hi,'bootstrap_ci_excludes_zero':boot_excl,'negative_seed_count':neg,'negative_seed_fraction':frac,'trajectory_fraction':traj_frac,'nested_effect_stable':nested_stable,'projected_pairs_for_80pct_power':req,'campaign_passed':bool(manifest.get('passed',False))}
        summary.append(row)
        shape_rows.append(row)
        power_rows.append({'n_traj':ntraj,'projected_disorder_pairs_for_80pct_power':req,'current_disorder_pairs':len(d),'recommended_trajectory_reps_next':max(reps,6),'recommended_ntraj_next':max(ntraj,64),'mean_fixed_effect_db':mean,'trajectory_fraction':traj_frac})
    sdf=pd.DataFrame(summary)
    final=sdf.sort_values('n_traj').tail(1).iloc[0].to_dict() if len(sdf) else {}
    pass_req=st4e.get('pass_requires',{})
    final_ntraj_ok=int(final.get('n_traj',0))>=int(pass_req.get('final_ntraj',max(ntraj_sweep)))
    neg_ok=float(final.get('mean_fixed_effect_db',np.nan))<0
    t_ok=bool(final.get('t_ci_excludes_zero',False))
    traj_ok=float(final.get('trajectory_fraction',1.0))<float(pass_req.get('trajectory_fraction_below',0.5))
    frac_ok=float(final.get('negative_seed_fraction',0.0))>=float(pass_req.get('negative_seed_fraction_at_least',0.75))
    passed=bool(final_ntraj_ok and neg_ok and t_ok and traj_ok and frac_ok)
    if passed:
        route='stage4f_confirmatory_passed_prepare_stage5_design_review'
    elif neg_ok and (t_ok or bool(final.get('bootstrap_ci_excludes_zero',False))):
        route='stage4f_signal_survives_needs_stage5_power'
    elif neg_ok:
        route='stage4f_directional_only_not_ready'
    else:
        route='stage4f_signal_not_stable_reconsider_route'
    readiness=pd.DataFrame([
        {'gate':'final_ntraj_ok','value':final_ntraj_ok},
        {'gate':'fixed_mean_negative','value':neg_ok},
        {'gate':'t_ci_excludes_zero','value':t_ok},
        {'gate':'trajectory_fraction_below_threshold','value':traj_ok},
        {'gate':'negative_seed_fraction_gate','value':frac_ok},
        {'gate':'stage4e_passed','value':passed},
        {'gate':'route','value':route},
    ])
    stage5=pd.DataFrame([{
        'target_shape':target_shape,
        'recommended_disorder_seeds':int(st4e.get('stage5_design',{}).get('recommended_disorder_seeds',32)),
        'recommended_trajectory_reps':int(st4e.get('stage5_design',{}).get('recommended_trajectory_reps',6)),
        'recommended_ntraj':int(st4e.get('stage5_design',{}).get('recommended_ntraj',64)),
        'fixed_time_primary':bool(st4e.get('stage5_design',{}).get('fixed_time_primary',True)),
        'min_time_secondary':bool(st4e.get('stage5_design',{}).get('min_time_secondary',True)),
        'decision_basis':'Advance only if trajectory fraction is controlled and fixed-time intervals remain negative.'
    }])
    save_dataframe(out/'stage4f_trajectory_scaling_summary.csv',sdf,raw)
    save_dataframe(out/'stage4f_shape_readiness.csv',pd.DataFrame(shape_rows),raw)
    save_dataframe(out/'stage4f_power_projection.csv',pd.DataFrame(power_rows),raw)
    save_dataframe(out/'stage4f_readiness_gates.csv',readiness,raw)
    save_dataframe(out/'stage4f_recommended_stage5_design.csv',stage5,raw)
    save_json(out/'stage4f_confirmatory_manifest.json',{'stage':'stage4f_high_trajectory_confirmatory_pilot','config':args.config,'target_shape':target_shape,'ntraj_sweep':ntraj_sweep,'trajectory_reps':reps,'disorder_seeds':seeds,'route':route,'passed':passed,'final_summary':final,'claim_scope':'trajectory-stabilization pilot only; no final publication claim'})
    print(f'stage4f high-trajectory confirmatory wrote {out}; route={route}; passed={passed}; final_ntraj={final.get("n_traj",None)}; traj_fraction={final.get("trajectory_fraction",None)}')
if __name__=='__main__':
    main()
