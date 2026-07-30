#!/usr/bin/env python
from __future__ import annotations
import argparse, json, sys, hashlib
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src')); sys.path.insert(0,str(ROOT/'scripts'))
from stage2_common import load_raw_config
from haxs.io.result_store import ensure_dir, save_dataframe, save_json
from haxs.validation.random_effects import balanced_random_effects_anova, bootstrap_hierarchical_ci


def paired_effects(finals: pd.DataFrame, metric='xi2_db_fixed') -> pd.DataFrame:
    a=finals[finals.label=='static_only'][['occupancy_idx','path_idx','phase_idx',metric]].rename(columns={metric:'static'})
    b=finals[finals.label=='mobile_plus_spin_density'][['occupancy_idx','path_idx','phase_idx',metric]].rename(columns={metric:'mobile_sd'})
    m=a.merge(b,on=['occupancy_idx','path_idx','phase_idx'])
    m['effect_db']=m['static']-m['mobile_sd']
    return m


def local_window(curves: pd.DataFrame, finals: pd.DataFrame, offsets):
    fixed_time=float(finals['fixed_time'].dropna().iloc[0]) if 'fixed_time' in finals.columns else 0.9227272727272726
    times=np.sort(curves['time'].unique())
    rows=[]
    for off in offsets:
        target=fixed_time+float(off); actual=float(times[np.argmin(np.abs(times-target))])
        sub=curves[np.isclose(curves.time, actual)]
        a=sub[sub.label=='static_only'][['occupancy_idx','path_idx','phase_idx','xi2_db']].rename(columns={'xi2_db':'static'})
        b=sub[sub.label=='mobile_plus_spin_density'][['occupancy_idx','path_idx','phase_idx','xi2_db']].rename(columns={'xi2_db':'mobile_sd'})
        m=a.merge(b,on=['occupancy_idx','path_idx','phase_idx']); m['effect_db']=m.static-m.mobile_sd
        stats=balanced_random_effects_anova(m)
        lo,hi=bootstrap_hierarchical_ci(m,n_boot=1000,seed=20260520+int(round(1000*float(off))))
        rows.append({'offset':float(off),'target_time':target,'actual_time':actual,'mean_effect_db':stats['mean_effect_db'],'hierarchical_ci_low':lo,'hierarchical_ci_high':hi,'negative':bool(hi<0.0)})
    return pd.DataFrame(rows)


def analyze_block(path: Path, block: str, st: dict, prefix: str):
    finals=pd.read_csv(path/f'{prefix}_finals.csv')
    curves=pd.read_csv(path/f'{prefix}_curves_all.csv')
    pe=paired_effects(finals)
    stats=balanced_random_effects_anova(pe)
    lo,hi=bootstrap_hierarchical_ci(pe,n_boot=int(st.get('bootstrap_samples',1000)),seed=9001 if block=='primary' else 9002)
    occ_means=pe.groupby('occupancy_idx').effect_db.mean()
    gates=st['gates']
    local=local_window(curves, finals, st.get('local_window_offsets',[-0.1,0,0.1])); local['block']=block
    row={**stats,'block':block,'hierarchical_ci_low':lo,'hierarchical_ci_high':hi,'occupancy_negative_fraction':float((occ_means<0).mean()),'absolute_mc_se_gate_pass':bool(stats['hierarchical_standard_error'] <= float(gates['absolute_mc_se_below'])),'fixed_time_ci_gate_pass':bool(hi < float(gates['hierarchical_ci_high_below'])),'occupancy_negative_gate_pass':bool((occ_means<0).mean() >= float(gates['occupancy_negative_fraction_at_least'])),'local_window_all_negative':bool(local['negative'].all())}
    row['block_pass_without_compatibility']=bool(row['absolute_mc_se_gate_pass'] and row['fixed_time_ci_gate_pass'] and row['occupancy_negative_gate_pass'] and row['local_window_all_negative'])
    occ_table=occ_means.reset_index().rename(columns={'effect_db':'occupancy_mean_effect_db'}); occ_table['block']=block
    return row, local, pe.assign(block=block), occ_table


def sha_file(p: Path) -> str:
    h=hashlib.sha256();
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def seed_audit(primary_reg: pd.DataFrame, confirm_reg: pd.DataFrame):
    rows=[]
    for col in ['occupancy_seed','hole_path_seed','phase_batch_seed','occupancy_hash','path_hash']:
        if col not in primary_reg.columns or col not in confirm_reg.columns: continue
        p=set(primary_reg[col].astype(str)); c=set(confirm_reg[col].astype(str))
        inter=sorted(p & c)[:20]
        rows.append({'stream':col,'primary_unique':len(p),'confirmation_unique':len(c),'overlap_count':len(p & c),'first_overlaps':';'.join(inter)})
    return pd.DataFrame(rows)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--config',default='configs/stage5c2eR/primary_I16_J6_K4.yaml')
    ap.add_argument('--primary',required=True)
    ap.add_argument('--locked-confirmation',required=True)
    ap.add_argument('--out',default='results/stage5c2eR/analysis')
    a=ap.parse_args(); raw=load_raw_config(a.config); st=raw['stage5c2eR']; out=ensure_dir(ROOT/a.out)
    prow,plocal,pe1,occ1=analyze_block(ROOT/a.primary,'primary',st,'stage5c2eR')
    crow,clocal,pe2,occ2=analyze_block(ROOT/a.locked_confirmation,'confirmation',st,'stage5c2d')
    block_table=pd.DataFrame([prow,crow])
    block_delta=abs(float(prow['mean_effect_db'])-float(crow['mean_effect_db']))
    compat=block_delta <= float(st['gates']['block_compatibility_abs_db_below'])
    # Equivalence screen: conservative normal approx using occupancy-level means.
    pocc=occ1['occupancy_mean_effect_db']; cocc=occ2['occupancy_mean_effect_db']
    diff=float(pocc.mean()-cocc.mean())
    se_diff=float(np.sqrt(pocc.var(ddof=1)/len(pocc)+cocc.var(ddof=1)/len(cocc))) if len(pocc)>1 and len(cocc)>1 else float('nan')
    eq_low=diff-1.645*se_diff if np.isfinite(se_diff) else float('nan')
    eq_high=diff+1.645*se_diff if np.isfinite(se_diff) else float('nan')
    equivalence_pass=bool(np.isfinite(eq_low) and eq_low >= -float(st['gates']['block_compatibility_abs_db_below']) and eq_high <= float(st['gates']['block_compatibility_abs_db_below']))
    block_table['block_delta_db']=block_delta; block_table['block_compatibility_pass']=compat; block_table['equivalence_90_low']=eq_low; block_table['equivalence_90_high']=eq_high; block_table['equivalence_interval_pass']=equivalence_pass
    local_table=pd.concat([plocal,clocal],ignore_index=True)
    primary_pass=bool(block_table[block_table.block=='primary'].block_pass_without_compatibility.iloc[0])
    confirmation_pass=bool(block_table[block_table.block=='confirmation'].block_pass_without_compatibility.iloc[0])
    passed=bool(primary_pass and confirmation_pass and compat and equivalence_pass)
    reasons=[]
    if not primary_pass: reasons.append('primary_hierarchical_gate_not_passed')
    if not confirmation_pass: reasons.append('locked_confirmation_gate_not_passed')
    if not compat: reasons.append('primary_confirmation_point_delta_incompatible')
    if not equivalence_pass: reasons.append('primary_confirmation_equivalence_interval_not_passed')
    if not reasons: reasons=['stage5c2eR_primary_relock_passed']
    save_dataframe(out/'stage5c2eR_random_effects_gate_table.csv', block_table, raw)
    save_dataframe(out/'stage5c2eR_local_window_table.csv', local_table, raw)
    save_dataframe(out/'stage5c2eR_paired_cell_effects.csv', pd.concat([pe1,pe2],ignore_index=True), raw)
    save_dataframe(out/'stage5c2eR_occupancy_effects.csv', pd.concat([occ1,occ2],ignore_index=True), raw)
    # Seed overlap audit for provenance, not a gate on locked legacy cells.
    try:
        preg=pd.read_csv(ROOT/a.primary/'stage5c2eR_seed_registry.csv')
        creg=pd.read_csv(ROOT/a.locked_confirmation/'stage5c2d_seed_registry.csv')
        sa=seed_audit(preg,creg)
        save_dataframe(out/'stage5c2eR_seed_namespace_audit.csv', sa, raw)
    except Exception as e:
        sa=pd.DataFrame([{'error':str(e)}]); save_dataframe(out/'stage5c2eR_seed_namespace_audit.csv', sa, raw)
    payload={'stage':'stage5c2eR_dominant_variance_precision_relock_decision','stage5c3_data_production_allowed':passed,'stage5d_broad_compute_allowed':False,'route':'stage5c3_design_review_can_be_requested' if passed else 'stage5c2eR_repair_or_stop','primary_confirmation_block_delta_db':block_delta,'equivalence_90_low':eq_low,'equivalence_90_high':eq_high,'reasons':reasons,'claim_scope':st.get('claim_scope','')}
    save_json(out/'stage5c2eR_decision.json', payload)
    print(json.dumps(payload, indent=2))
if __name__=='__main__': main()
