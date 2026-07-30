#!/usr/bin/env python
from __future__ import annotations
import argparse, sys, json
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from haxs.io.result_store import ensure_dir, save_dataframe, save_json

def j(path): return json.loads(Path(path).read_text())
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--results',default='results/stage4a_lite'); ap.add_argument('--out',default='results/stage4a_lite/decision')
    args=ap.parse_args(); r=ROOT/args.results; out=ensure_dir(ROOT/args.out)
    dtwa=j(r/'dtwa_validation/dtwa_validation_manifest.json'); ed=j(r/'ed_dtwa_gate/ed_dtwa_manifest.json')
    camp=j(r/'publication_campaign/stage4_publication_campaign_manifest.json'); diag=j(r/'stability_diagnosis/stage4a_stability_manifest.json')
    dtwa_pass=bool(dtwa.get('passed',False)); ed_pass=bool(ed.get('passed',False))
    fixed_neg=int(diag.get('fixed_negative_shapes',0)); fixed_ci=int(diag.get('fixed_ci_shapes',0)); prom=int(diag.get('promising_shapes',0)); traj=int(diag.get('trajectory_dominated_shapes',0))
    if dtwa_pass and ed_pass and fixed_neg>=3:
        route='stage4a_diagnosis_complete_prepare_targeted_stage4b'
    else:
        route='stage4a_repair_required_before_stage4b'
    table=pd.DataFrame([{'gate':'dtwa_validation','value':dtwa_pass,'passed':dtwa_pass}, {'gate':'ed_dtwa_gate','value':ed_pass,'passed':ed_pass}, {'gate':'fixed_negative_shapes','value':fixed_neg,'passed':fixed_neg>=3}, {'gate':'fixed_ci_shapes','value':fixed_ci,'passed':fixed_ci>=1}, {'gate':'promising_shapes','value':prom,'passed':prom>=1}, {'gate':'trajectory_dominated_shapes','value':traj,'passed':traj==0}])
    save_dataframe(out/'stage4a_decision_table.csv',table)
    save_json(out/'stage4a_decision.json',{'stage':'stage4a','route':route,'dtwa_passed':dtwa_pass,'ed_dtwa_passed':ed_pass,'publication_campaign_passed':bool(camp.get('passed',False)),'fixed_negative_shapes':fixed_neg,'fixed_ci_shapes':fixed_ci,'promising_shapes':prom,'trajectory_dominated_shapes':traj,'recommendation':'Do not claim publication success. Use diagnostics to design a targeted Stage 4B run.'})
    print(f'stage4a decision wrote {out}; route={route}')
if __name__=='__main__': main()
