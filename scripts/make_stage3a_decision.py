#!/usr/bin/env python
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from haxs.io.result_store import ensure_dir, save_dataframe, save_json

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--results',default='results/stage3a_lite'); ap.add_argument('--out',default='results/stage3a_lite/decision'); args=ap.parse_args()
    r=ROOT/args.results; out=ensure_dir(ROOT/args.out)
    val=pd.read_csv(r/'dtwa_validation/dtwa_validation_summary.csv')
    dtwa_pass=bool(val['passed'].astype(bool).all())
    paired_pass=False; core_diff=None; core_ci=None
    paired_path=r/'paired_mechanism/paired_mechanism_inference.csv'
    if paired_path.exists():
        p=pd.read_csv(paired_path)
        core=p[(p.group_a=='static_only')&(p.group_b=='mobile_plus_spin_density')]
        if len(core):
            row=core.iloc[0]; core_diff=float(row['paired_mean_difference_a_minus_b']); core_ci=[float(row['bootstrap_ci_low']),float(row['bootstrap_ci_high'])]
            paired_pass=bool(row['ci_excludes_zero']) and core_diff < 0
    route='stage3a_repair_passed_ready_for_stage3b' if (dtwa_pass and paired_pass) else ('stage3a_dtwa_passed_mechanism_inconclusive' if dtwa_pass else 'stage3a_dtwa_repair_failed')
    table=pd.DataFrame([{'gate':'dtwa_validation','passed':dtwa_pass},{'gate':'paired_static_vs_mobile_plus_sd','passed':paired_pass}])
    save_dataframe(out/'stage3a_decision_table.csv', table, {'stage':'stage3a'})
    save_json(out/'stage3a_decision.json', {'route':route,'dtwa_validation_passed':dtwa_pass,'paired_mechanism_core_passed':paired_pass,'core_static_minus_mobile_plus_sd':core_diff,'core_ci':core_ci})
    print(f'stage3a decision wrote {out}; route={route}')
if __name__=='__main__': main()
