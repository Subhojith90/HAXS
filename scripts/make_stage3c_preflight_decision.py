#!/usr/bin/env python
from __future__ import annotations
import argparse, sys, json, os
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from haxs.io.result_store import ensure_dir, save_dataframe, save_json

def scan_stale(root: Path):
    rows=[]
    for p in root.rglob('*.csv'):
        s=str(p)
        if 'stage3c_preflight' in s: continue
        try:
            df=pd.read_csv(p,nrows=5)
        except Exception:
            continue
        if 'spin_length' in df.columns and len(df)>1:
            val=float(df['spin_length'].iloc[1])
            if 0.54 <= val <= 0.62:
                rows.append({'file':str(p.relative_to(root)),'first_step_spin_length':val,'stale_collapse_signature':True})
    return pd.DataFrame(rows)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--results',default='results/stage3c_preflight'); ap.add_argument('--out',default='results/stage3c_preflight/decision')
    args=ap.parse_args(); res=ROOT/args.results; out=ensure_dir(ROOT/args.out)
    stale=scan_stale(ROOT)
    if len(stale): save_dataframe(out/'stale_output_findings.csv',stale,{})
    ed=json.loads((res/'ed_dtwa_gate'/'ed_dtwa_manifest.json').read_text())
    nested=json.loads((res/'fixed_time_nested'/'stage3c_fixed_time_nested_manifest.json').read_text())
    pair=pd.read_csv(res/'fixed_time_nested'/'stage3c_fixed_time_pair_effects.csv')
    fixed=pair[pair.metric=='xi2_db_fixed']
    minm=pair[pair.metric=='xi2_db_min']
    table=pd.DataFrame([
      {'gate':'no_stale_collapse_outputs','value':int(len(stale)),'passed':len(stale)==0},
      {'gate':'ed_dtwa_gate','value':ed.get('xi2_db_rmse'), 'passed':bool(ed.get('passed'))},
      {'gate':'fixed_time_negative_shapes','value':nested.get('primary_fixed_negative_shapes'), 'passed':int(nested.get('primary_fixed_negative_shapes',0))>=3},
      {'gate':'fixed_time_ci_excluding_zero_shapes','value':nested.get('primary_fixed_ci_excluding_zero_shapes'), 'passed':int(nested.get('primary_fixed_ci_excluding_zero_shapes',0))>=2},
      {'gate':'nested_uncertainty_stable_shapes','value':nested.get('nested_stable_shapes'), 'passed':int(nested.get('nested_stable_shapes',0))>=2},
    ])
    passed=bool(table['passed'].all())
    route='stage3c_preflight_passed_ready_for_stage3d_design' if passed else 'stage3c_preflight_failed_repair_before_scale'
    save_dataframe(out/'stage3c_preflight_decision_table.csv',table,{})
    save_json(out/'stage3c_preflight_decision.json',{'stage':'stage3c_preflight','route':route,'passed':passed,'stale_findings':int(len(stale)),'ed_dtwa_passed':bool(ed.get('passed')),'fixed_time_negative_shapes':nested.get('primary_fixed_negative_shapes'),'fixed_time_ci_excluding_zero_shapes':nested.get('primary_fixed_ci_excluding_zero_shapes'),'nested_stable_shapes':nested.get('nested_stable_shapes'),'mean_fixed_effect':float(fixed.paired_mean_difference_a_minus_b.mean()) if len(fixed) else None,'mean_min_effect':float(minm.paired_mean_difference_a_minus_b.mean()) if len(minm) else None})
    print(f'stage3c decision wrote {out}; route={route}')
if __name__=='__main__': main()
