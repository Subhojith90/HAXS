#!/usr/bin/env python
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from haxs.io.result_store import ensure_dir, save_dataframe, save_json

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--results',default='results/stage4d_lite'); ap.add_argument('--out',default='results/stage4d_lite/decision')
    args=ap.parse_args(); base=ROOT/args.results; out=ensure_dir(ROOT/args.out)
    dtwa=json.loads((base/'dtwa_validation/dtwa_validation_manifest.json').read_text())
    ed=json.loads((base/'ed_dtwa_gate/ed_dtwa_manifest.json').read_text())
    pilot=json.loads((base/'stage4d_publication_pilot_manifest.json').read_text())
    readiness=pd.read_csv(base/'stage4d_publication_readiness.csv')
    route=pilot.get('route','unknown')
    if not (dtwa.get('passed') and ed.get('passed')):
        route='stage4d_validation_failed_stop'
    decision={'stage':'stage4d_targeted_publication_pilot_decision','route':route,'dtwa_gate_passed':bool(dtwa.get('passed')),'ed_dtwa_gate_passed':bool(ed.get('passed')),'pilot':pilot,'publication_claim_allowed':route=='stage4d_pilot_passed_prepare_stage5_design_review','claim_scope':'mechanism/diagnostic surrogate only; no constructive recovery/no-go/exact mobile-hole claim'}
    table=pd.DataFrame([{'metric':k,'value':str(v)} for k,v in decision.items() if k!='pilot'] + [{'metric':f'pilot_{k}','value':str(v)} for k,v in pilot.items()])
    save_dataframe(out/'stage4d_decision_table.csv',table,{})
    save_json(out/'stage4d_decision.json',decision)
    print(f'stage4d decision wrote {out}; route={route}')
if __name__=='__main__': main()
