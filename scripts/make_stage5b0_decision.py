#!/usr/bin/env python
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from haxs.io.result_store import ensure_dir, save_dataframe, save_json

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--results',default='results/stage5b0_lite'); ap.add_argument('--out',default='results/stage5b0_lite/decision'); args=ap.parse_args()
    res=ROOT/args.results; out=ensure_dir(ROOT/args.out)
    gates=pd.read_csv(res/'trajectory_fraction_lock/stage5b0_readiness_gates.csv')
    route=str(gates[gates.gate=='route'].value.iloc[0]) if len(gates[gates.gate=='route']) else 'stage5b0_unknown'
    lock=bool(str(gates[gates.gate=='trajectory_fraction_lock_passed'].value.iloc[0]).lower()=='true') if len(gates[gates.gate=='trajectory_fraction_lock_passed']) else False
    five=bool(str(gates[gates.gate=='five_label_mechanism_pilot_passed'].value.iloc[0]).lower()=='true') if len(gates[gates.gate=='five_label_mechanism_pilot_passed']) else False
    summary=pd.read_csv(res/'trajectory_fraction_lock/stage5b0_trajectory_lock_summary.csv')
    decision={'stage':'stage5b0_trajectory_fraction_lock_mechanism_pilot','route':route,'trajectory_fraction_lock_passed':lock,'five_label_mechanism_pilot_passed':five,'publication_claim_allowed':False,'stage5b_full_compute_allowed':bool(lock and five),'primary_trajectory_fraction':float(summary[summary.block=='primary'].trajectory_fraction.iloc[0]),'replication_trajectory_fraction':float(summary[summary.block=='replication'].trajectory_fraction.iloc[0])}
    save_json(out/'stage5b0_decision.json',decision)
    save_dataframe(out/'stage5b0_decision_table.csv',pd.DataFrame([decision]),{})
    print(f'stage5b0 decision wrote {out}; route={route}')
if __name__=='__main__': main()
