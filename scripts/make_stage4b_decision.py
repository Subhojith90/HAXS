#!/usr/bin/env python
from __future__ import annotations
import argparse, sys, json
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from haxs.io.result_store import ensure_dir, save_dataframe, save_json

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--results',default='results/stage4b_lite'); ap.add_argument('--out',default='results/stage4b_lite/decision')
    args=ap.parse_args(); base=ROOT/args.results; out=ensure_dir(ROOT/args.out)
    # validation gates
    dtwa=json.loads((base/'dtwa_validation/dtwa_validation_manifest.json').read_text()) if (base/'dtwa_validation/dtwa_validation_manifest.json').exists() else {}
    ed=json.loads((base/'ed_dtwa_gate/ed_dtwa_manifest.json').read_text()) if (base/'ed_dtwa_gate/ed_dtwa_manifest.json').exists() else {}
    camp=json.loads((base/'publication_campaign/stage4_publication_campaign_manifest.json').read_text())
    stab=json.loads((base/'stability_diagnosis/stage4a_stability_manifest.json').read_text())
    diag=pd.read_csv(base/'stability_diagnosis/stage4a_shape_stability_diagnosis.csv')
    pair=pd.read_csv(base/'publication_campaign/stage4_primary_pair_effects.csv')
    primary=pair[pair.metric=='xi2_db_fixed']
    fixed_negative=int((primary.mean_effect_db<0).sum())
    fixed_ci=int(primary.ci_excludes_zero.sum())
    promising=int(diag.diagnosis.fillna('').str.contains('promising').sum()) if len(diag) else 0
    traj_dom=int(diag.diagnosis.fillna('').str.contains('trajectory_dominated').sum()) if len(diag) else 0
    mean_effect=float(primary.mean_effect_db.mean()) if len(primary) else float('nan')
    route='stage4b_checkpoint_ready_for_supervisor_review'
    if not (dtwa.get('passed',False) and ed.get('passed',False)):
        route='stage4b_validation_failed_stop'
    elif promising < 1 or fixed_negative < 2:
        route='stage4b_mechanism_too_weak_stop_or_redesign'
    elif traj_dom >= max(1,promising):
        route='stage4b_needs_trajectory_scaling_before_claims'
    table=pd.DataFrame([
        {'metric':'dtwa_gate_passed','value':bool(dtwa.get('passed',False))},
        {'metric':'ed_dtwa_gate_passed','value':bool(ed.get('passed',False))},
        {'metric':'fixed_negative_shapes','value':fixed_negative},
        {'metric':'fixed_ci_excluding_zero_shapes','value':fixed_ci},
        {'metric':'promising_shapes','value':promising},
        {'metric':'trajectory_dominated_shapes','value':traj_dom},
        {'metric':'mean_fixed_time_primary_effect_db','value':mean_effect},
        {'metric':'route','value':route},
    ])
    save_dataframe(out/'stage4b_decision_table.csv',table,{})
    save_json(out/'stage4b_decision.json',{'stage':'stage4b_targeted_mechanism_checkpoint','route':route,'dtwa_gate_passed':bool(dtwa.get('passed',False)),'ed_dtwa_gate_passed':bool(ed.get('passed',False)),'publication_campaign_passed':bool(camp.get('passed',False)),'fixed_negative_shapes':fixed_negative,'fixed_ci_excluding_zero_shapes':fixed_ci,'promising_shapes':promising,'trajectory_dominated_shapes':traj_dom,'mean_fixed_time_primary_effect_db':mean_effect,'interpretation':'targeted checkpoint; supervisor review before any large compute or manuscript claim'})
    print(f'stage4b decision wrote {out}; route={route}; promising_shapes={promising}; fixed_negative_shapes={fixed_negative}')
if __name__=='__main__': main()
