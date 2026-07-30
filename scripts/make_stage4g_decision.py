#!/usr/bin/env python
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from haxs.io.result_store import ensure_dir, save_dataframe, save_json

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--results',default='results/stage4g_lite'); ap.add_argument('--out',default='results/stage4g_lite/decision')
    args=ap.parse_args(); res=ROOT/args.results; out=ensure_dir(ROOT/args.out)
    man=json.loads((res/'disorder_seed_expansion/stage4g_disorder_seed_manifest.json').read_text())
    summ=pd.read_csv(res/'disorder_seed_expansion/stage4g_trajectory_scaling_summary.csv')
    final=summ.sort_values('n_traj').tail(1).iloc[0].to_dict()
    route=man.get('route','unknown')
    decision={
        'stage':'stage4g_3x3x2_disorder_seed_expansion',
        'route':route,
        'passed':bool(man.get('passed',False)),
        'target_shape':man.get('target_shape','3x3x2'),
        'final_ntraj':int(final.get('n_traj',0)),
        'final_mean_fixed_effect_db':float(final.get('mean_fixed_effect_db',float('nan'))),
        'final_t_ci_excludes_zero':bool(final.get('t_ci_excludes_zero',False)),
        'final_trajectory_fraction':float(final.get('trajectory_fraction',float('nan'))),
        'final_negative_seed_fraction':float(final.get('negative_seed_fraction',float('nan'))),
        'publication_claim_allowed':False,
        'stage5_design_review_ready': route in ['stage4g_disorder_seed_passed_prepare_stage5_design_review','stage4g_signal_survives_needs_stage5_power'],
        'recommended_next_action':'Supervisor review before Stage 5; do not claim final mechanism proof.'
    }
    tab=pd.DataFrame([{'key':k,'value':v} for k,v in decision.items()])
    save_json(out/'stage4g_decision.json',decision); save_dataframe(out/'stage4g_decision_table.csv',tab,{})
    print(f'stage4g decision wrote {out}; route={route}')
if __name__=='__main__': main()
