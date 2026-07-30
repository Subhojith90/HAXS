#!/usr/bin/env python
from __future__ import annotations
import argparse, sys
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from haxs.io.result_store import ensure_dir, save_dataframe, save_json

def asbool(x): return str(x).lower()=='true'
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--results',default='results/stage5b1_lite'); ap.add_argument('--out',default='results/stage5b1_lite/decision'); args=ap.parse_args()
    res=ROOT/args.results; out=ensure_dir(ROOT/args.out)
    gates=pd.read_csv(res/'replicated_five_label/stage5b1_readiness_gates.csv')
    def g(name, default=False):
        m=gates[gates.gate==name]
        return default if len(m)==0 else m.value.iloc[0]
    route=str(g('route','stage5b1_unknown'))
    decision={'stage':'stage5b1_replicated_five_label_mechanism_decomposition','route':route,'core_contrast_replicated':asbool(g('core_contrast_replicated',False)),'component_contrasts_replicated':asbool(g('component_contrasts_replicated',False)),'block_compatibility_passed':asbool(g('block_compatibility_passed',False)),'local_fixed_time_window_passed':asbool(g('local_fixed_time_window_passed',False)),'stage5b1_passed':asbool(g('stage5b1_passed',False)),'stage5b_design_review_allowed':asbool(g('stage5b_design_review_allowed',False)),'stage5c_broad_compute_allowed':False,'publication_claim_allowed':False}
    save_json(out/'stage5b1_decision.json',decision)
    save_dataframe(out/'stage5b1_decision_table.csv',pd.DataFrame([decision]),{})
    print(f'stage5b1 decision wrote {out}; route={route}')
if __name__=='__main__': main()
