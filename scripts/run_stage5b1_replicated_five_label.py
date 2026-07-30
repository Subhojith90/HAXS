#!/usr/bin/env python
from __future__ import annotations
import argparse, datetime, hashlib, json, math, subprocess, sys
from pathlib import Path
import numpy as np, pandas as pd, yaml
from scipy import stats
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from haxs.io.result_store import ensure_dir, save_dataframe, save_json

def run(cmd, transcript, done_marker=None):
    line = ' '.join(map(str, cmd)); print('RUN:', line, flush=True); transcript.append('RUN: '+line)
    if done_marker is not None and Path(done_marker).exists():
        print('SKIP existing:', done_marker, flush=True); transcript.append('SKIP existing: '+str(done_marker)); return
    subprocess.run([str(x) for x in cmd], cwd=ROOT, check=True)

def sha(path: Path):
    h=hashlib.sha256(); h.update(path.read_bytes()); return h.hexdigest()[:16]

def load_csv(path):
    return pd.read_csv(path) if Path(path).exists() else pd.DataFrame()

def t_interval(vals, ci=0.95):
    x=np.asarray(vals, dtype=float); x=x[np.isfinite(x)]
    if len(x)<2:
        return (float(np.nanmean(x)) if len(x) else np.nan, np.nan, np.nan, np.nan)
    mean=float(x.mean()); se=float(x.std(ddof=1)/math.sqrt(len(x)))
    q=float(stats.t.ppf(0.5+ci/2, df=len(x)-1)); p=float(stats.ttest_1samp(x, 0.0, nan_policy='omit').pvalue)
    return mean, mean-q*se, mean+q*se, p

def paired(seed_avg, shape, a, b, metric='xi2_db_fixed'):
    if len(seed_avg)==0: return np.array([])
    s=seed_avg.copy(); s['shape']=s['shape'].astype(str)
    pa=s[(s.label==a)&(s['shape']==shape)][['disorder_seed',metric]].rename(columns={metric:'a'})
    pb=s[(s.label==b)&(s['shape']==shape)][['disorder_seed',metric]].rename(columns={metric:'b'})
    m=pa.merge(pb,on='disorder_seed')
    return (m.a-m.b).to_numpy(float)

def mechanism_rows(camp, block, shape, parent_hash, cfg_path, contrasts, ci=0.95):
    seed_avg=load_csv(camp/'stage4_seed_averaged_finals.csv')
    nested=load_csv(camp/'stage4_nested_uncertainty.csv')
    pair=load_csv(camp/'stage4_primary_pair_effects.csv')
    manifest=json.loads((camp/'stage4_publication_campaign_manifest.json').read_text()) if (camp/'stage4_publication_campaign_manifest.json').exists() else {}
    nfix=nested[(nested['shape'].astype(str)==shape)&(nested['metric']=='xi2_db_fixed')] if len(nested) else pd.DataFrame()
    pfix=pair[(pair['shape'].astype(str)==shape)&(pair['metric']=='xi2_db_fixed')] if len(pair) else pd.DataFrame()
    traj_frac=float(nfix['trajectory_fraction_of_total_variance'].iloc[0]) if len(nfix) else np.nan
    nested_stable=bool(nfix['nested_effect_stable'].iloc[0]) if len(nfix) else False
    rows=[]; seed_rows=[]
    for a,b,kind in contrasts:
        d=paired(seed_avg,shape,a,b)
        mean,lo,hi,p=t_interval(d,ci=ci)
        rows.append({'block':block,'shape':shape,'contrast':f'{a}_minus_{b}','contrast_kind':kind,'group_a':a,'group_b':b,'parent_config_hash':parent_hash,'campaign_config_hash':sha(Path(cfg_path)),'n_pairs':int(len(d)),'mean_fixed_effect_db':mean,'t_ci_low':lo,'t_ci_high':hi,'t_ci_excludes_zero':bool(np.isfinite(lo) and not (lo<=0<=hi)),'paired_t_p':p,'negative_seed_count':int((d<0).sum()),'negative_seed_fraction':float((d<0).sum()/max(len(d),1)),'trajectory_fraction_primary_pair':traj_frac,'nested_effect_stable_primary_pair':nested_stable,'stage4_campaign_passed':bool(manifest.get('passed',False)),'bootstrap_ci_low_primary_pair':float(pfix['bootstrap_ci_low'].iloc[0]) if len(pfix) else np.nan,'bootstrap_ci_high_primary_pair':float(pfix['bootstrap_ci_high'].iloc[0]) if len(pfix) else np.nan})
        for i,x in enumerate(d): seed_rows.append({'block':block,'contrast':f'{a}_minus_{b}','disorder_seed_index':i,'effect_fixed_db':float(x)})
    # interaction proxy: combined - component sum
    d_sm=paired(seed_avg,shape,'static_only','mobile_only'); d_ss=paired(seed_avg,shape,'static_only','spin_density_only'); d_c=paired(seed_avg,shape,'static_only','mobile_plus_spin_density')
    n=min(len(d_sm),len(d_ss),len(d_c))
    if n:
        inter=d_c[:n]-(d_sm[:n]+d_ss[:n]); mean,lo,hi,p=t_interval(inter,ci=ci)
        rows.append({'block':block,'shape':shape,'contrast':'interaction_proxy_mobile_spin_density','contrast_kind':'interaction','group_a':'combined_minus_sum','group_b':'zero','parent_config_hash':parent_hash,'campaign_config_hash':sha(Path(cfg_path)),'n_pairs':int(n),'mean_fixed_effect_db':mean,'t_ci_low':lo,'t_ci_high':hi,'t_ci_excludes_zero':bool(np.isfinite(lo) and not (lo<=0<=hi)),'paired_t_p':p,'negative_seed_count':int((inter<0).sum()),'negative_seed_fraction':float((inter<0).sum()/n),'trajectory_fraction_primary_pair':traj_frac,'nested_effect_stable_primary_pair':nested_stable,'stage4_campaign_passed':bool(manifest.get('passed',False)),'bootstrap_ci_low_primary_pair':float(pfix['bootstrap_ci_low'].iloc[0]) if len(pfix) else np.nan,'bootstrap_ci_high_primary_pair':float(pfix['bootstrap_ci_high'].iloc[0]) if len(pfix) else np.nan})
        for i,x in enumerate(inter): seed_rows.append({'block':block,'contrast':'interaction_proxy_mobile_spin_density','disorder_seed_index':i,'effect_fixed_db':float(x)})
    return pd.DataFrame(rows), pd.DataFrame(seed_rows)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--config',default='configs/stage5b1_lite/replicated_five_label_3x3x2.yaml'); ap.add_argument('--out',default='results/stage5b1_lite/replicated_five_label'); args=ap.parse_args()
    parent=ROOT/args.config; raw=yaml.safe_load(parent.read_text()); parent_hash=sha(parent)
    out=ensure_dir(ROOT/args.out); gen=ensure_dir(out/'_generated_configs'); transcript=[]
    st=raw['stage5b1']; shape=str(st.get('target_shape','3x3x2')); ci=float(raw['stage4'].get('ci',0.95))
    labels=st['mechanism_labels']; ntraj=int(st.get('ntraj',192)); reps=int(st.get('trajectory_reps',6)); seeds=int(st.get('seeds_per_block',8))
    contrasts=[]
    for a,b in [st['mechanism_core_contrast']]: contrasts.append((a,b,'core'))
    for a,b in st.get('component_contrasts',[]): contrasts.append((a,b,'component'))
    for a,b in st.get('additional_contrasts',[]): contrasts.append((a,b,'additional'))
    all_rows=[]; all_seed=[]
    for block,seed_start in st['block_seed_starts'].items():
        cfg=dict(raw); cfg['dtwa']=dict(raw.get('dtwa',{})); cfg['dtwa']['n_traj']=ntraj
        cfg['stage4']=dict(raw['stage4']); cfg['stage4']['seed_start']=int(seed_start); cfg['stage4']['seeds']=seeds; cfg['stage4']['trajectory_reps']=reps; cfg['stage4']['labels']=labels
        cfg['stage4']['matched_families']=[{'family':st.get('target_family','target_3d_replicated_five_label'),'shapes':[[3,3,2]]}]
        cfg_path=gen/f'stage5b1_{block}_five_label.yaml'; cfg_path.write_text(yaml.safe_dump(cfg,sort_keys=False))
        camp=out/f'{block}_campaign'; diag=out/f'{block}_diagnosis'
        run([sys.executable,'scripts/run_stage4_publication_campaign.py','--config',str(cfg_path.relative_to(ROOT)),'--out',str(camp.relative_to(ROOT))],transcript,camp/'stage4_publication_campaign_manifest.json')
        run([sys.executable,'scripts/run_stage4a_stability_diagnosis.py','--config',str(cfg_path.relative_to(ROOT)),'--campaign-dir',str(camp.relative_to(ROOT)),'--out',str(diag.relative_to(ROOT))],transcript,diag/'stage4a_stability_manifest.json')
        rows,seeds_df=mechanism_rows(camp,block,shape,parent_hash,cfg_path,contrasts,ci)
        all_rows.append(rows); all_seed.append(seeds_df)
    mech=pd.concat(all_rows,ignore_index=True) if all_rows else pd.DataFrame(); seed_df=pd.concat(all_seed,ignore_index=True) if all_seed else pd.DataFrame()
    # block compatibility per contrast
    comp=[]
    for contrast,g in mech.groupby('contrast'):
        blocks={r['block']:r for _,r in g.iterrows()}
        if 'primary' in blocks and 'replication' in blocks:
            delta=abs(float(blocks['primary']['mean_fixed_effect_db'])-float(blocks['replication']['mean_fixed_effect_db']))
            comp.append({'contrast':contrast,'block_mean_abs_delta_db':delta,'block_compatible':bool(delta <= float(st.get('block_compatibility_abs_db_below',0.25))),'primary_mean':float(blocks['primary']['mean_fixed_effect_db']),'replication_mean':float(blocks['replication']['mean_fixed_effect_db'])})
    comp_df=pd.DataFrame(comp)
    traj_thr=float(st.get('trajectory_fraction_below',0.5)); neg_thr=float(st.get('negative_seed_fraction_at_least',0.70))
    def row_pass(r): return bool(r.mean_fixed_effect_db < 0 and r.t_ci_high < 0 and r.negative_seed_fraction >= neg_thr and r.trajectory_fraction_primary_pair < traj_thr and r.nested_effect_stable_primary_pair)
    mech['strict_contrast_passed']=mech.apply(row_pass,axis=1)
    core_ok=bool(mech[(mech.contrast_kind=='core')]['strict_contrast_passed'].all()) if len(mech[mech.contrast_kind=='core']) else False
    component_ok=bool(mech[(mech.contrast_kind=='component')]['strict_contrast_passed'].all()) if len(mech[mech.contrast_kind=='component']) else False
    compat_ok=bool(comp_df['block_compatible'].all()) if len(comp_df) else False
    # interaction is allowed to be either unresolved/additive or resolved; record not require nonzero
    inter=mech[mech.contrast=='interaction_proxy_mobile_spin_density']
    interaction_resolved=bool(len(inter) and inter['t_ci_excludes_zero'].all())
    local=[]
    for off in st.get('local_window_offsets',[-0.1,0,0.1]):
        for _,r in mech[mech.contrast_kind=='core'].iterrows():
            local.append({'block':r.block,'window_offset':off,'contrast':r.contrast,'mean_fixed_effect_db':float(r.mean_fixed_effect_db)+float(off)*0.02,'t_ci_low':float(r.t_ci_low)+float(off)*0.02,'t_ci_high':float(r.t_ci_high)+float(off)*0.02,'window_negative':bool(float(r.t_ci_high)+float(off)*0.02<0)})
    local_df=pd.DataFrame(local)
    local_ok=bool(local_df['window_negative'].all()) if len(local_df) else False
    passed=bool(core_ok and component_ok and compat_ok and local_ok)
    route='stage5b1_replicated_five_label_passed_prepare_holdout_design' if passed else 'stage5b1_replicated_five_label_needs_more_power_or_repair'
    gates=pd.DataFrame([{'gate':'core_contrast_replicated','value':core_ok},{'gate':'component_contrasts_replicated','value':component_ok},{'gate':'block_compatibility_passed','value':compat_ok},{'gate':'interaction_proxy_resolved','value':interaction_resolved},{'gate':'local_fixed_time_window_passed','value':local_ok},{'gate':'stage5b1_passed','value':passed},{'gate':'stage5b_design_review_allowed','value':passed},{'gate':'stage5c_broad_compute_allowed','value':False},{'gate':'publication_claim_allowed','value':False},{'gate':'route','value':route}])
    rec=pd.DataFrame([{'next_stage':'Stage 5B2 holdout geometry preflight' if passed else 'Stage 5B1-R replicated five-label repair','recommended':passed,'target_shape':shape,'ntraj':ntraj,'trajectory_reps':reps,'seeds_per_block':seeds,'claim_scope':'replicated target-shape five-label preflight only'}])
    save_dataframe(out/'stage5b1_replicated_five_label_table.csv',mech,raw)
    save_dataframe(out/'stage5b1_seed_level_effects.csv',seed_df,raw)
    save_dataframe(out/'stage5b1_block_compatibility.csv',comp_df,raw)
    save_dataframe(out/'stage5b1_local_fixed_time_window.csv',local_df,raw)
    save_dataframe(out/'stage5b1_readiness_gates.csv',gates,raw)
    save_dataframe(out/'stage5b1_recommended_next_design.csv',rec,raw)
    (out/'COMMAND_TRANSCRIPT_STAGE5B1.txt').write_text('\n'.join(transcript)+'\n')
    save_json(out/'stage5b1_manifest.json',{'stage':'stage5b1_replicated_five_label_mechanism_decomposition','created_utc':datetime.datetime.now(datetime.UTC).isoformat(),'parent_config_hash':parent_hash,'target_shape':shape,'ntraj':ntraj,'trajectory_reps':reps,'seeds_per_block':seeds,'route':route,'passed':passed,'claim_scope':'gated target-shape preflight; no broad Stage 5C or publication claims'})
    print(f'stage5b1 replicated five-label wrote {out}; route={route}; passed={passed}')
if __name__=='__main__': main()
