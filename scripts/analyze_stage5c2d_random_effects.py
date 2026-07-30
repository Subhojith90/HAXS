
#!/usr/bin/env python
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import numpy as np
import pandas as pd
import yaml
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

def local_window(curves: pd.DataFrame, offsets):
    fixed_time=float(curves.get('fixed_time', pd.Series([np.nan])).iloc[0]) if 'fixed_time' in curves.columns else 0.9227272727272726
    # infer from nearest central time used in finals if absent
    times=np.sort(curves['time'].unique())
    if not np.isfinite(fixed_time): fixed_time=float(times[int(round(0.65*(len(times)-1)))])
    rows=[]
    for off in offsets:
        target=fixed_time+float(off); actual=float(times[np.argmin(np.abs(times-target))])
        sub=curves[np.isclose(curves.time, actual)]
        a=sub[sub.label=='static_only'][['occupancy_idx','path_idx','phase_idx','xi2_db']].rename(columns={'xi2_db':'static'})
        b=sub[sub.label=='mobile_plus_spin_density'][['occupancy_idx','path_idx','phase_idx','xi2_db']].rename(columns={'xi2_db':'mobile_sd'})
        m=a.merge(b,on=['occupancy_idx','path_idx','phase_idx']); m['effect_db']=m.static-m.mobile_sd
        stats=balanced_random_effects_anova(m)
        lo,hi=bootstrap_hierarchical_ci(m,n_boot=1000,seed=991+int(round(1000*float(off))))
        rows.append({'offset':float(off),'target_time':target,'actual_time':actual,'mean_effect_db':stats['mean_effect_db'],'hierarchical_ci_low':lo,'hierarchical_ci_high':hi,'negative':bool(hi<0.0)})
    return pd.DataFrame(rows)

def analyze_block(path: Path, block: str, st: dict):
    finals=pd.read_csv(path/'stage5c2d_finals.csv'); curves=pd.read_csv(path/'stage5c2d_curves_all.csv')
    pe=paired_effects(finals)
    stats=balanced_random_effects_anova(pe)
    lo,hi=bootstrap_hierarchical_ci(pe,n_boot=int(st.get('bootstrap_samples',1000)),seed=777 if block=='primary' else 888)
    occ_means=pe.groupby('occupancy_idx').effect_db.mean()
    gates=st['gates']
    row={**stats,'block':block,'hierarchical_ci_low':lo,'hierarchical_ci_high':hi,'occupancy_negative_fraction':float((occ_means<0).mean()),'absolute_mc_se_gate_pass':bool(stats['hierarchical_standard_error'] <= float(gates['absolute_mc_se_below'])),'fixed_time_ci_gate_pass':bool(hi < float(gates['hierarchical_ci_high_below'])),'occupancy_negative_gate_pass':bool((occ_means<0).mean() >= float(gates['occupancy_negative_fraction_at_least']))}
    local=local_window(curves, st.get('local_window_offsets',[-0.1,0,0.1])); local['block']=block
    row['local_window_all_negative']=bool(local['negative'].all())
    row['block_pass_without_compatibility']=bool(row['absolute_mc_se_gate_pass'] and row['fixed_time_ci_gate_pass'] and row['occupancy_negative_gate_pass'] and row['local_window_all_negative'])
    return row, local, pe

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--config',default='configs/stage5c2d_lite/nested_core_3x3x3.yaml'); ap.add_argument('--primary',required=True); ap.add_argument('--confirmation',required=True); ap.add_argument('--out',default='results/stage5c2d_lite/analysis')
    a=ap.parse_args(); raw=load_raw_config(a.config); st=raw['stage5c2d']; out=ensure_dir(ROOT/a.out)
    prow,plocal,pe1=analyze_block(ROOT/a.primary,'primary',st); crow,clocal,pe2=analyze_block(ROOT/a.confirmation,'confirmation',st)
    block_table=pd.DataFrame([prow,crow])
    block_delta=abs(float(prow['mean_effect_db'])-float(crow['mean_effect_db']))
    compat=block_delta <= float(st['gates']['block_compatibility_abs_db_below'])
    block_table['block_delta_db']=block_delta; block_table['block_compatibility_pass']=compat
    local_table=pd.concat([plocal,clocal],ignore_index=True)
    primary_pass=bool(block_table[block_table.block=='primary'].block_pass_without_compatibility.iloc[0])
    confirmation_pass=bool(block_table[block_table.block=='confirmation'].block_pass_without_compatibility.iloc[0])
    passed=bool(primary_pass and confirmation_pass and compat)
    reasons=[]
    if not primary_pass: reasons.append('primary_hierarchical_gate_not_passed')
    if not confirmation_pass: reasons.append('confirmation_hierarchical_gate_not_passed')
    if not compat: reasons.append('primary_confirmation_block_incompatible')
    if not reasons: reasons=['stage5c2d_confirmatory_relock_passed']
    save_dataframe(out/'stage5c2d_random_effects_gate_table.csv', block_table, raw)
    save_dataframe(out/'stage5c2d_local_window_table.csv', local_table, raw)
    seed_effects=pd.concat([pe1.assign(block='primary'), pe2.assign(block='confirmation')], ignore_index=True)
    save_dataframe(out/'stage5c2d_paired_cell_effects.csv', seed_effects, raw)
    payload={'stage':'stage5c2d_random_stream_repair_decision','stage5c3_design_review_allowed':passed,'stage5d_broad_compute_allowed':False,'route':'stage5c3_design_review_can_be_requested' if passed else 'stage5c2d_repair_or_stop','primary_confirmation_block_delta_db':block_delta,'reasons':reasons,'claim_scope':st.get('claim_scope','')}
    save_json(out/'stage5c2d_decision.json', payload)
    print(json.dumps(payload, indent=2))
if __name__=='__main__': main()
