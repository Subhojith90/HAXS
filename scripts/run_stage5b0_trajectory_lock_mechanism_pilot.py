#!/usr/bin/env python
from __future__ import annotations
import argparse, hashlib, math, subprocess, sys, json, datetime
from pathlib import Path
import numpy as np, pandas as pd, yaml
from scipy import stats
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from haxs.io.result_store import ensure_dir, save_dataframe, save_json

def run(cmd, transcript, done_marker=None):
    line=' '.join(map(str,cmd)); print('RUN:', line, flush=True); transcript.append('RUN: '+line)
    if done_marker is not None and Path(done_marker).exists():
        print('SKIP existing:', done_marker, flush=True); transcript.append('SKIP existing: '+str(done_marker)); return
    subprocess.run([str(x) for x in cmd], cwd=ROOT, check=True)

def sha(path:Path):
    h=hashlib.sha256(); h.update(path.read_bytes()); return h.hexdigest()[:16]

def load_csv(path):
    return pd.read_csv(path) if Path(path).exists() else pd.DataFrame()

def t_interval(vals, ci=0.95):
    x=np.asarray(vals,dtype=float); x=x[np.isfinite(x)]
    if len(x)<2: return (float(np.nanmean(x)) if len(x) else np.nan, np.nan, np.nan, np.nan)
    mean=float(x.mean()); se=float(x.std(ddof=1)/math.sqrt(len(x)))
    q=float(stats.t.ppf(0.5+ci/2, df=len(x)-1)); p=float(stats.ttest_1samp(x,0.0,nan_policy='omit').pvalue)
    return mean, mean-q*se, mean+q*se, p

def paired_diffs(seed_avg, shape, a, b, metric='xi2_db_fixed'):
    if seed_avg is None or len(seed_avg)==0: return np.array([])
    pa=seed_avg[(seed_avg.label==a)&(seed_avg['shape'].astype(str)==shape)][['disorder_seed',metric]].rename(columns={metric:'a'})
    pb=seed_avg[(seed_avg.label==b)&(seed_avg['shape'].astype(str)==shape)][['disorder_seed',metric]].rename(columns={metric:'b'})
    m=pa.merge(pb,on='disorder_seed')
    return (m.a-m.b).to_numpy(float)

def summarize_campaign(camp, cfg_path, parent_hash, block, ntraj, shape, a, b, ci):
    pair=load_csv(camp/'stage4_primary_pair_effects.csv')
    nested=load_csv(camp/'stage4_nested_uncertainty.csv')
    seed_avg=load_csv(camp/'stage4_seed_averaged_finals.csv')
    manifest=json.loads((camp/'stage4_publication_campaign_manifest.json').read_text()) if (camp/'stage4_publication_campaign_manifest.json').exists() else {}
    pfix=pair[(pair['shape'].astype(str)==shape)&(pair['metric']=='xi2_db_fixed')] if len(pair) else pd.DataFrame()
    nfix=nested[(nested['shape'].astype(str)==shape)&(nested['metric']=='xi2_db_fixed')] if len(nested) else pd.DataFrame()
    d=paired_diffs(seed_avg, shape, a, b, 'xi2_db_fixed')
    mean,lo,hi,p=t_interval(d,ci=ci)
    neg=int((d<0).sum()) if len(d) else 0; neg_frac=neg/max(len(d),1)
    traj_frac=float(nfix['trajectory_fraction_of_total_variance'].iloc[0]) if len(nfix) else np.nan
    nested_stable=bool(nfix['nested_effect_stable'].iloc[0]) if len(nfix) else False
    boot_lo=float(pfix['bootstrap_ci_low'].iloc[0]) if len(pfix) else np.nan
    boot_hi=float(pfix['bootstrap_ci_high'].iloc[0]) if len(pfix) else np.nan
    boot_excl=bool(pfix['ci_excludes_zero'].iloc[0]) if len(pfix) else False
    seed_rows=[{'block':block,'n_traj':ntraj,'shape':shape,'disorder_seed_index':i,'effect_fixed_db':float(x)} for i,x in enumerate(d)]
    return {
        'block':block,'n_traj':ntraj,'shape':shape,'parent_config_hash':parent_hash,'campaign_config_hash':sha(Path(cfg_path)),
        'disorder_pairs':int(len(d)),'trajectory_reps':int(manifest.get('trajectory_reps',-1)),
        'mean_fixed_effect_db':mean,'t_ci_low':lo,'t_ci_high':hi,'t_ci_excludes_zero':bool(np.isfinite(lo) and not (lo<=0<=hi)),
        'paired_t_p':p,'bootstrap_ci_low':boot_lo,'bootstrap_ci_high':boot_hi,'bootstrap_ci_excludes_zero':boot_excl,
        'negative_seed_count':neg,'negative_seed_fraction':float(neg_frac),'trajectory_fraction':traj_frac,
        'nested_effect_stable':nested_stable,'stage4_campaign_passed':bool(manifest.get('passed',False)),
        'stage4_fixed_negative_shapes':int(manifest.get('fixed_negative_shapes',-1)),
        'stage4_fixed_ci_shapes':int(manifest.get('fixed_ci_excluding_zero_shapes',-1)),
        'stage4_nested_stable_shapes':int(manifest.get('nested_stable_shapes',-1)),
    }, seed_rows

def block_ok(r, neg_thr, traj_thr):
    return bool(r['mean_fixed_effect_db']<0 and r['t_ci_excludes_zero'] and r['bootstrap_ci_excludes_zero'] and r['negative_seed_fraction']>=neg_thr and r['trajectory_fraction']<traj_thr and r['nested_effect_stable'])

def failure_reasons(r, neg_thr, traj_thr):
    reasons=[]
    if not r['mean_fixed_effect_db']<0: reasons.append('mean_not_negative')
    if not r['t_ci_excludes_zero']: reasons.append('t_ci_crosses_zero')
    if not r['bootstrap_ci_excludes_zero']: reasons.append('bootstrap_ci_crosses_zero')
    if not r['negative_seed_fraction']>=neg_thr: reasons.append('negative_seed_fraction_low')
    if not r['trajectory_fraction']<traj_thr: reasons.append('trajectory_fraction_high')
    if not r['nested_effect_stable']: reasons.append('nested_effect_not_stable')
    return ';'.join(reasons) if reasons else 'none'

def mechanism_table(camp, shape, labels, ci=0.95):
    seed_avg=load_csv(camp/'stage4_seed_averaged_finals.csv')
    rows=[]
    for a,b in [('static_only','mobile_only'),('static_only','spin_density_only'),('static_only','mobile_plus_spin_density'),('mobile_only','mobile_plus_spin_density'),('spin_density_only','mobile_plus_spin_density'),('static_only','everything')]:
        if a not in labels or b not in labels: continue
        d=paired_diffs(seed_avg, shape, a, b, 'xi2_db_fixed')
        mean,lo,hi,p=t_interval(d,ci=ci)
        rows.append({'shape':shape,'contrast':f'{a}_minus_{b}','group_a':a,'group_b':b,'n_pairs':len(d),'mean_fixed_effect_db':mean,'t_ci_low':lo,'t_ci_high':hi,'paired_t_p':p,'negative_seed_fraction':float((d<0).sum()/max(len(d),1))})
    # interaction proxy: static->mobile+SD minus sum of static->mobile and static->SD
    try:
        d_sm=paired_diffs(seed_avg, shape, 'static_only','mobile_only')
        d_ss=paired_diffs(seed_avg, shape, 'static_only','spin_density_only')
        d_smsd=paired_diffs(seed_avg, shape, 'static_only','mobile_plus_spin_density')
        n=min(len(d_sm),len(d_ss),len(d_smsd))
        if n:
            inter=d_smsd[:n]-(d_sm[:n]+d_ss[:n])
            mean,lo,hi,p=t_interval(inter,ci=ci)
            rows.append({'shape':shape,'contrast':'interaction_proxy_mobile_spin_density','group_a':'static_vs_mobile_plus_sd','group_b':'sum_static_vs_components','n_pairs':n,'mean_fixed_effect_db':mean,'t_ci_low':lo,'t_ci_high':hi,'paired_t_p':p,'negative_seed_fraction':float((inter<0).sum()/n)})
    except Exception:
        pass
    return pd.DataFrame(rows)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--config',default='configs/stage5b0_lite/trajectory_fraction_lock_and_five_label_3x3x2.yaml')
    ap.add_argument('--out',default='results/stage5b0_lite')
    args=ap.parse_args()
    parent=ROOT/args.config; raw=yaml.safe_load(parent.read_text()); parent_hash=sha(parent)
    out=ensure_dir(ROOT/args.out); lock=ensure_dir(out/'trajectory_fraction_lock'); gen=ensure_dir(lock/'_generated_configs')
    st=raw.get('stage5b0',{}); target=str(st.get('target_shape','3x3x2'))
    ntraj=int(st.get('ntraj_lock',128)); reps=int(st.get('trajectory_reps_lock',8)); seeds=int(st.get('seeds_per_block',8))
    ci=float(raw.get('stage4',{}).get('ci',0.95)); a,b=raw['stage4']['primary_pair']
    transcript=[]; summary=[]; seed_rows=[]
    blocks=[('primary',int(st.get('primary_seed_start',91001))),('replication',int(st.get('replication_seed_start',99001)))]
    for block, seed_start in blocks:
        cfg=dict(raw); cfg['dtwa']=dict(raw.get('dtwa',{})); cfg['dtwa']['n_traj']=ntraj
        cfg['stage4']=dict(raw.get('stage4',{})); cfg['stage4']['seed_start']=seed_start; cfg['stage4']['seeds']=seeds; cfg['stage4']['trajectory_reps']=reps
        cfg['stage4']['labels']=['static_only','mobile_plus_spin_density','everything']
        cfg['stage4']['matched_families']=[{'family':st.get('target_family','target_3d_trajectory_fraction_lock'),'shapes':[[3,3,2]]}]
        cfg_path=gen/f'stage5b0_{block}_trajectory_lock_ntraj_{ntraj}.yaml'; cfg_path.write_text(yaml.safe_dump(cfg,sort_keys=False))
        camp=lock/f'{block}_campaign_ntraj_{ntraj}'; diag=lock/f'{block}_diagnosis_ntraj_{ntraj}'
        run([sys.executable,'scripts/run_stage4_publication_campaign.py','--config',str(cfg_path.relative_to(ROOT)),'--out',str(camp.relative_to(ROOT))], transcript, camp/'stage4_publication_campaign_manifest.json')
        run([sys.executable,'scripts/run_stage4a_stability_diagnosis.py','--config',str(cfg_path.relative_to(ROOT)),'--campaign-dir',str(camp.relative_to(ROOT)),'--out',str(diag.relative_to(ROOT))], transcript, diag/'stage4a_stability_manifest.json')
        row,sr=summarize_campaign(camp,cfg_path,parent_hash,block,ntraj,target,a,b,ci); summary.append(row); seed_rows.extend(sr)
    sdf=pd.DataFrame(summary); seed_df=pd.DataFrame(seed_rows)
    traj_thr=float(st.get('trajectory_fraction_below',0.5)); neg_thr=float(st.get('negative_seed_fraction_at_least',0.70)); compat_thr=float(st.get('block_compatibility_abs_db_below',0.25))
    sdf['stage5b0_block_passed']=[block_ok(r,neg_thr,traj_thr) for r in sdf.to_dict('records')]
    sdf['failure_reasons']=[failure_reasons(r,neg_thr,traj_thr) for r in sdf.to_dict('records')]
    prim=sdf[sdf.block=='primary'].iloc[0].to_dict(); repl=sdf[sdf.block=='replication'].iloc[0].to_dict()
    block_delta=abs(float(prim['mean_fixed_effect_db'])-float(repl['mean_fixed_effect_db']))
    compatible=bool(block_delta<=compat_thr)
    lock_passed=bool(sdf['stage5b0_block_passed'].all() and compatible)
    five_dir=ensure_dir(out/'five_label_mechanism')
    five_ran=False; mech=pd.DataFrame(); five_passed=False
    if lock_passed or not bool(st.get('run_five_label_only_if_lock_passes',True)):
        labels=st.get('mechanism_labels',['static_only','mobile_only','spin_density_only','mobile_plus_spin_density','everything'])
        cfg=dict(raw); cfg['dtwa']=dict(raw.get('dtwa',{})); cfg['dtwa']['n_traj']=ntraj
        cfg['stage4']=dict(raw.get('stage4',{})); cfg['stage4']['seed_start']=int(st.get('five_label_seed_start',101001)); cfg['stage4']['seeds']=int(st.get('five_label_seeds',8)); cfg['stage4']['trajectory_reps']=int(st.get('five_label_trajectory_reps',4)); cfg['stage4']['labels']=labels
        cfg['stage4']['matched_families']=[{'family':st.get('target_family','target_3d_trajectory_fraction_lock'),'shapes':[[3,3,2]]}]
        cfg_path=gen/'stage5b0_five_label_3x3x2.yaml'; cfg_path.write_text(yaml.safe_dump(cfg,sort_keys=False))
        camp=five_dir/'campaign'; diag=five_dir/'diagnosis'
        run([sys.executable,'scripts/run_stage4_publication_campaign.py','--config',str(cfg_path.relative_to(ROOT)),'--out',str(camp.relative_to(ROOT))], transcript, camp/'stage4_publication_campaign_manifest.json')
        run([sys.executable,'scripts/run_stage4a_stability_diagnosis.py','--config',str(cfg_path.relative_to(ROOT)),'--campaign-dir',str(camp.relative_to(ROOT)),'--out',str(diag.relative_to(ROOT))], transcript, diag/'stage4a_stability_manifest.json')
        mech=mechanism_table(camp,target,labels,ci=ci)
        five_ran=True
        # preflight success: primary static-vs-mobile+SD negative and at least one component contrast informative
        core=mech[mech.contrast=='static_only_minus_mobile_plus_spin_density']
        five_passed=bool(len(core) and float(core.mean_fixed_effect_db.iloc[0])<0 and float(core.t_ci_high.iloc[0])<0)
    gates=pd.DataFrame([
        {'gate':'primary_block_passed','value':bool(sdf[sdf.block=='primary'].stage5b0_block_passed.iloc[0])},
        {'gate':'replication_block_passed','value':bool(sdf[sdf.block=='replication'].stage5b0_block_passed.iloc[0])},
        {'gate':'block_effects_compatible','value':compatible},
        {'gate':'trajectory_fraction_lock_passed','value':lock_passed},
        {'gate':'five_label_mechanism_pilot_ran','value':five_ran},
        {'gate':'five_label_mechanism_pilot_passed','value':five_passed},
    ])
    if lock_passed and five_passed:
        route='stage5b0_passed_prepare_stage5b_full_design_review'
    elif lock_passed:
        route='stage5b0_lock_passed_mechanism_pilot_needs_review'
    else:
        route='stage5b0_trajectory_fraction_lock_needs_more_power'
    gates.loc[len(gates)]={'gate':'route','value':route}
    rec=pd.DataFrame([{'next_stage':'Stage 5B full five-label mechanism decomposition','recommended':bool(lock_passed and five_passed),'target_shape':target,'recommended_ntraj':ntraj,'recommended_disorder_seeds':max(seeds,16),'recommended_trajectory_reps':reps,'labels':'static_only,mobile_only,spin_density_only,mobile_plus_spin_density,everything','decision_basis':'Proceed only after target trajectory-fraction lock and five-label preflight are satisfied.'}])
    save_dataframe(lock/'stage5b0_trajectory_lock_summary.csv',sdf,raw)
    save_dataframe(lock/'stage5b0_seed_level_effects.csv',seed_df,raw)
    save_dataframe(lock/'stage5b0_readiness_gates.csv',gates,raw)
    save_dataframe(five_dir/'stage5b0_five_label_mechanism_table.csv',mech,raw)
    save_dataframe(out/'stage5b0_recommended_stage5b_design.csv',rec,raw)
    (lock/'COMMAND_TRANSCRIPT_STAGE5B0.txt').write_text('\n'.join(transcript)+'\n')
    save_json(lock/'stage5b0_manifest.json',{'stage':'stage5b0_trajectory_fraction_lock_mechanism_pilot','created_utc':datetime.datetime.now(datetime.UTC).isoformat(),'config':args.config,'parent_config_hash':parent_hash,'target_shape':target,'ntraj_lock':ntraj,'seeds_per_block':seeds,'trajectory_reps_lock':reps,'block_mean_abs_delta_db':block_delta,'trajectory_fraction_threshold':traj_thr,'lock_passed':lock_passed,'five_label_pilot_ran':five_ran,'five_label_pilot_passed':five_passed,'route':route,'claim_scope':'gated preflight only; no broad mechanism, finite-size, or publication claim'})
    print(f'stage5b0 trajectory lock/mechanism pilot wrote {out}; route={route}; lock_passed={lock_passed}; five_label_ran={five_ran}')
if __name__=='__main__': main()
