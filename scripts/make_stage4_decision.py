#!/usr/bin/env python
from __future__ import annotations
import argparse, json
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--results',default='results/stage4_lite'); ap.add_argument('--out',default='results/stage4_lite/decision')
    args=ap.parse_args(); res=ROOT/args.results; out=ROOT/args.out; out.mkdir(parents=True,exist_ok=True)
    dtwa=json.loads((res/'dtwa_validation/dtwa_validation_manifest.json').read_text()); ed=json.loads((res/'ed_dtwa_gate/ed_dtwa_manifest.json').read_text()); camp=json.loads((res/'publication_campaign/stage4_publication_campaign_manifest.json').read_text())
    p=pd.read_csv(res/'publication_campaign/stage4_primary_pair_effects.csv'); primary=p[p.metric=='xi2_db_fixed']
    route='stage4_publication_candidate_internal_audit' if dtwa.get('passed') and ed.get('passed') and camp.get('passed') else 'stage4_not_ready_repair_required'
    summary={'route':route,'dtwa_passed':bool(dtwa.get('passed')),'ed_dtwa_passed':bool(ed.get('passed')),'campaign_passed':bool(camp.get('passed')),'mean_fixed_primary_effect_db':float(primary.mean_effect_db.mean()) if len(primary) else None,'fixed_negative_shapes':camp.get('fixed_negative_shapes'),'fixed_ci_excluding_zero_shapes':camp.get('fixed_ci_excluding_zero_shapes'),'nested_stable_shapes':camp.get('nested_stable_shapes'),'publication_claim_allowed': route=='stage4_publication_candidate_internal_audit','claim_scope':'validated DTWA surrogate mechanism evidence only'}
    (out/'stage4_decision.json').write_text(json.dumps(summary,indent=2)); pd.DataFrame([summary]).to_csv(out/'stage4_decision_table.csv',index=False)
    print(f'stage4 decision wrote {out}; route={route}')
if __name__=='__main__': main()
