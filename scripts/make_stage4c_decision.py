#!/usr/bin/env python
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from haxs.io.result_store import ensure_dir, save_dataframe, save_json

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--results',default='results/stage4c_lite'); ap.add_argument('--out',default='results/stage4c_lite/decision')
    args=ap.parse_args(); base=ROOT/args.results; out=ensure_dir(ROOT/args.out)
    dtwa=json.loads((base/'dtwa_validation/dtwa_validation_manifest.json').read_text())
    ed=json.loads((base/'ed_dtwa_gate/ed_dtwa_manifest.json').read_text())
    camp=json.loads((base/'publication_campaign/stage4_publication_campaign_manifest.json').read_text())
    stab=json.loads((base/'stability_diagnosis/stage4a_stability_manifest.json').read_text())
    traj=json.loads((base/'trajectory_scaling/stage4c_trajectory_scaling_manifest.json').read_text())
    diag=pd.read_csv(base/'stability_diagnosis/stage4a_shape_stability_diagnosis.csv')
    nested=pd.read_csv(base/'publication_campaign/stage4_nested_uncertainty.csv')
    bad_shape=bool(diag['shape'].astype(str).str.contains(r'\(|,\)').any()) if 'shape' in diag else True
    nested_fixed=nested[nested.metric=='xi2_db_fixed']
    corrected_traj_dom=int((nested_fixed.trajectory_fraction_of_total_variance>0.5).sum())
    diag_traj_dom=int(diag.diagnosis.fillna('').str.contains('trajectory_dominated').sum()) if len(diag) else -1
    decision_consistent=bool(corrected_traj_dom==diag_traj_dom)
    fixed_negative=int(stab.get('fixed_negative_shapes',0)); fixed_ci=int(stab.get('fixed_ci_shapes',0)); promising=int(stab.get('promising_shapes',0))
    route='stage4c0_repair_complete_supervisor_checkpoint'
    if bad_shape or not decision_consistent:
        route='stage4c0_decision_repair_failed_stop'
    elif not (dtwa.get('passed') and ed.get('passed')):
        route='stage4c0_validation_failed_stop'
    elif int(traj.get('final_trajectory_dominated_shapes',99)) >= 3:
        route='stage4c0_trajectory_dominated_need_more_trajectory_scaling'
    elif fixed_negative>=2 and promising>=1:
        route='stage4c0_ready_for_targeted_disorder_seed_pilot'
    table=pd.DataFrame([
        {'metric':'dtwa_gate_passed','value':bool(dtwa.get('passed'))},
        {'metric':'ed_dtwa_gate_passed','value':bool(ed.get('passed'))},
        {'metric':'shape_bookkeeping_clean','value':not bad_shape},
        {'metric':'decision_nested_consistent','value':decision_consistent},
        {'metric':'corrected_trajectory_dominated_shapes','value':corrected_traj_dom},
        {'metric':'fixed_negative_shapes','value':fixed_negative},
        {'metric':'fixed_ci_shapes','value':fixed_ci},
        {'metric':'promising_shapes','value':promising},
        {'metric':'trajectory_scaling_final_ntraj','value':traj.get('final_ntraj')},
        {'metric':'trajectory_scaling_final_traj_dominated_shapes','value':traj.get('final_trajectory_dominated_shapes')},
        {'metric':'route','value':route},
    ])
    save_dataframe(out/'stage4c0_decision_table.csv',table,{})
    save_json(out/'stage4c0_decision.json',{'stage':'stage4c0_decision_code_repair_trajectory_scaling_preflight','route':route,'dtwa_gate_passed':bool(dtwa.get('passed')),'ed_dtwa_gate_passed':bool(ed.get('passed')),'shape_bookkeeping_clean':not bad_shape,'decision_nested_consistent':decision_consistent,'corrected_trajectory_dominated_shapes':corrected_traj_dom,'fixed_negative_shapes':fixed_negative,'fixed_ci_shapes':fixed_ci,'promising_shapes':promising,'trajectory_scaling':traj,'claim_scope':'diagnostic preflight only; no publication/full-scale approval by this package alone'})
    print(f'stage4c decision wrote {out}; route={route}; corrected_traj_dom={corrected_traj_dom}')
if __name__=='__main__': main()
