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
    ap=argparse.ArgumentParser(); ap.add_argument('--results',default='results/stage5b0R_lite'); ap.add_argument('--out',default='results/stage5b0R_lite/decision'); args=ap.parse_args()
    res=ROOT/args.results; out=ensure_dir(ROOT/args.out)
    gates=pd.read_csv(res/'adaptive_trajectory_fraction_lock/stage5b0R_readiness_gates.csv')
    route=str(gates[gates.gate=='route'].value.iloc[0]) if len(gates[gates.gate=='route']) else 'stage5b0R_unknown'
    lock=asbool(gates[gates.gate=='trajectory_fraction_lock_passed'].value.iloc[0]) if len(gates[gates.gate=='trajectory_fraction_lock_passed']) else False
    five=asbool(gates[gates.gate=='five_label_mechanism_pilot_passed'].value.iloc[0]) if len(gates[gates.gate=='five_label_mechanism_pilot_passed']) else False
    summary=pd.read_csv(res/'adaptive_trajectory_fraction_lock/stage5b0R_adaptive_lock_summary.csv')
    selected=summary[summary.candidate_lock_passed==True]
    if len(selected)==0: selected=summary[summary.n_traj==summary.n_traj.max()]
    decision={'stage':'stage5b0R_adaptive_trajectory_fraction_lock_mechanism_pilot','route':route,'trajectory_fraction_lock_passed':bool(lock),'five_label_mechanism_pilot_passed':bool(five),'publication_claim_allowed':False,'stage5b_full_compute_allowed':bool(lock and five),'selected_ntraj':int(selected.n_traj.max()) if len(selected) else None,'primary_trajectory_fraction':float(selected[selected.block=='primary'].trajectory_fraction.iloc[0]) if len(selected[selected.block=='primary']) else None,'replication_trajectory_fraction':float(selected[selected.block=='replication'].trajectory_fraction.iloc[0]) if len(selected[selected.block=='replication']) else None}
    save_json(out/'stage5b0R_decision.json',decision)
    save_dataframe(out/'stage5b0R_decision_table.csv',pd.DataFrame([decision]),{})
    print(f'stage5b0R decision wrote {out}; route={route}')
if __name__=='__main__': main()
