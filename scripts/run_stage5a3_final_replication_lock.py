#!/usr/bin/env python
from __future__ import annotations
import argparse, hashlib, math, subprocess, sys
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
    manifest=yaml.safe_load((camp/'stage4_publication_campaign_manifest.json').read_text()) if (camp/'stage4_publication_campaign_manifest.json').exists() else {}
    pfix=pair[(pair['shape'].astype(str)==shape)&(pair['metric']=='xi2_db_fixed')] if len(pair) else pd.DataFrame()
    pmin=pair[(pair['shape'].astype(str)==shape)&(pair['metric']=='xi2_db_min')] if len(pair) else pd.DataFrame()
    nfix=nested[(nested['shape'].astype(str)==shape)&(nested['metric']=='xi2_db_fixed')] if len(nested) else pd.DataFrame()
    d=paired_diffs(seed_avg, shape, a, b, 'xi2_db_fixed')
    dmin=paired_diffs(seed_avg, shape, a, b, 'xi2_db_min')
    mean,lo,hi,p=t_interval(d,ci=ci); minmean,minlo,minhi,minp=t_interval(dmin,ci=ci)
    neg=int((d<0).sum()) if len(d) else 0; neg_frac=neg/max(len(d),1)
    traj_frac=float(nfix['trajectory_fraction_of_total_variance'].iloc[0]) if len(nfix) else np.nan
    nested_stable=bool(nfix['nested_effect_stable'].iloc[0]) if len(nfix) else False
    boot_lo=float(pfix['bootstrap_ci_low'].iloc[0]) if len(pfix) else np.nan
    boot_hi=float(pfix['bootstrap_ci_high'].iloc[0]) if len(pfix) else np.nan
    boot_excl=bool(pfix['ci_excludes_zero'].iloc[0]) if len(pfix) else False
    sd=float(np.std(d,ddof=1)) if len(d)>1 else np.nan
    zcrit=float(stats.norm.ppf(0.975)); zpow=float(stats.norm.ppf(0.80))
    req=int(math.ceil(((zcrit+zpow)*sd/max(abs(mean),1e-12))**2)) if np.isfinite(sd) and abs(mean)>1e-12 else -1
    seed_rows=[]
    for i,x in enumerate(d):
        seed_rows.append({'block':block,'n_traj':ntraj,'shape':shape,'disorder_seed_index':i,'effect_fixed_db':float(x)})
    return {
        'block':block,'n_traj':ntraj,'shape':shape,'parent_config_hash':parent_hash,'campaign_config_hash':sha(Path(cfg_path)),
        'disorder_pairs':int(len(d)),'trajectory_reps':int(manifest.get('trajectory_reps',-1)),'mean_fixed_effect_db':mean,
        't_ci_low':lo,'t_ci_high':hi,'t_ci_excludes_zero':bool(np.isfinite(lo) and not (lo<=0<=hi)),
        'paired_t_p':p,'bootstrap_ci_low':boot_lo,'bootstrap_ci_high':boot_hi,'bootstrap_ci_excludes_zero':boot_excl,
        'negative_seed_count':neg,'negative_seed_fraction':float(neg_frac),'trajectory_fraction':traj_frac,
        'nested_effect_stable':nested_stable,'projected_pairs_for_80pct_power':req,
        'min_time_mean_effect_db':minmean,'min_time_t_ci_low':minlo,'min_time_t_ci_high':minhi,'min_time_p':minp,
        'campaign_passed':bool(manifest.get('passed',False))
    }, seed_rows

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--config',default='configs/stage5a3_lite/final_replication_lock_3x3x2.yaml')
    ap.add_argument('--out',default='results/stage5a3_lite/final_replication_lock')
    args=ap.parse_args()
    parent=ROOT/args.config; raw=yaml.safe_load(parent.read_text()); parent_hash=sha(parent)
    out=ensure_dir(ROOT/args.out); gen=ensure_dir(out/'_generated_configs')
    st=raw.get('stage5a',{}); target=str(st.get('target_shape','3x3x2'))
    ntraj=int(st.get('ntraj_lock',128))
    reps=int(st.get('trajectory_reps',raw.get('stage4',{}).get('trajectory_reps',6)))
    seeds=int(st.get('seeds_per_block',raw.get('stage4',{}).get('seeds',12)))
    ci=float(raw.get('stage4',{}).get('ci',0.95)); a,b=raw['stage4']['primary_pair']
    transcript=[]; summary=[]; seed_rows=[]
    blocks=[('primary',int(st.get('primary_seed_start',75001))),('replication',int(st.get('replication_seed_start',85001)))]
    for block, seed_start in blocks:
        cfg=dict(raw); cfg['dtwa']=dict(raw.get('dtwa',{})); cfg['dtwa']['n_traj']=ntraj
        cfg['stage4']=dict(raw.get('stage4',{})); cfg['stage4']['seed_start']=seed_start; cfg['stage4']['seeds']=seeds; cfg['stage4']['trajectory_reps']=reps
        cfg['stage4']['matched_families']=[{'family':st.get('target_family','target_3d_replication_lock'),'shapes':[[3,3,2]]}]
        cfg_path=gen/f'stage5a3_{block}_ntraj_{ntraj}.yaml'; cfg_path.write_text(yaml.safe_dump(cfg,sort_keys=False))
        camp=out/f'{block}_campaign_ntraj_{ntraj}'; diag=out/f'{block}_diagnosis_ntraj_{ntraj}'
        run([sys.executable,'scripts/run_stage4_publication_campaign.py','--config',str(cfg_path.relative_to(ROOT)),'--out',str(camp.relative_to(ROOT))],transcript, camp/'stage4_publication_campaign_manifest.json')
        run([sys.executable,'scripts/run_stage4a_stability_diagnosis.py','--config',str(cfg_path.relative_to(ROOT)),'--campaign-dir',str(camp.relative_to(ROOT)),'--out',str(diag.relative_to(ROOT))],transcript, diag/'stage4a_stability_manifest.json')
        row, sr=summarize_campaign(camp,cfg_path,parent_hash,block,ntraj,target,a,b,ci); summary.append(row); seed_rows.extend(sr)
    sdf=pd.DataFrame(summary); seed_df=pd.DataFrame(seed_rows)
    prim=sdf[sdf.block=='primary'].iloc[0].to_dict(); repl=sdf[sdf.block=='replication'].iloc[0].to_dict()
    traj_thr=float(st.get('trajectory_fraction_below',0.5)); neg_thr=float(st.get('negative_seed_fraction_at_least',0.7)); compat_thr=float(st.get('block_compatibility_abs_db_below',0.5))
    def block_ok(r):
        return bool(r['mean_fixed_effect_db']<0 and r['t_ci_excludes_zero'] and r['bootstrap_ci_excludes_zero'] and r['negative_seed_fraction']>=neg_thr and r['trajectory_fraction']<traj_thr and r['nested_effect_stable'])
    primary_ok=block_ok(prim); repl_ok=block_ok(repl)
    block_delta=abs(float(prim['mean_fixed_effect_db'])-float(repl['mean_fixed_effect_db']))
    block_compatible=bool(block_delta<=compat_thr)
    passed=bool(primary_ok and repl_ok and block_compatible)
    route='stage5a3_passed_prepare_stage5b_mechanism_decomposition' if passed else ('stage5a3_directional_replication_lock_needs_more_power' if repl['mean_fixed_effect_db']<0 and prim['mean_fixed_effect_db']<0 else 'stage5a3_replication_lock_failed_reconsider_route')
    gates=pd.DataFrame([
        {'gate':'primary_block_passed','value':primary_ok},
        {'gate':'replication_block_passed','value':repl_ok},
        {'gate':'block_effects_compatible','value':block_compatible},
        {'gate':'stage5a3_passed','value':passed},
        {'gate':'route','value':route},
    ])
    rec=pd.DataFrame([{'next_stage':'Stage 5B high-stat mechanism decomposition','recommended':bool(passed),'target_shape':target,'recommended_ntraj':ntraj,'recommended_disorder_seeds':max(seeds,16),'recommended_trajectory_reps':reps,'labels':'static_only,mobile_only,spin_density_only,mobile_plus_spin_density,everything','decision_basis':'Proceed only if both primary and independent replication blocks pass at locked ntraj.'}])
    save_dataframe(out/'stage5a3_replication_lock_summary.csv',sdf,raw)
    save_dataframe(out/'stage5a3_seed_level_effects.csv',seed_df,raw)
    save_dataframe(out/'stage5a3_readiness_gates.csv',gates,raw)
    save_dataframe(out/'stage5a3_recommended_stage5b_design.csv',rec,raw)
    (out/'COMMAND_TRANSCRIPT_STAGE5A3.txt').write_text('\n'.join(transcript)+'\n')
    save_json(out/'stage5a3_manifest.json',{'stage':'stage5a3_final_replication_lock','config':args.config,'parent_config_hash':parent_hash,'target_shape':target,'ntraj_lock':ntraj,'blocks':[b for b,_ in blocks],'seeds_per_block':seeds,'trajectory_reps':reps,'block_mean_abs_delta_db':block_delta,'block_compatibility_threshold_db':compat_thr,'route':route,'passed':passed,'claim_scope':'final target-shape replication lock only; no publication, finite-size, or broad mechanism claim'})
    print(f'stage5a3 final replication lock wrote {out}; route={route}; passed={passed}; ntraj={ntraj}')
if __name__=='__main__': main()
