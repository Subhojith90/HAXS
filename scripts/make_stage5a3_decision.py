#!/usr/bin/env python
from pathlib import Path
import argparse, json
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--results',default='results/stage5a3_lite'); ap.add_argument('--out',default='results/stage5a3_lite/decision'); args=ap.parse_args()
    base=ROOT/args.results/'final_replication_lock'; out=ROOT/args.out; out.mkdir(parents=True,exist_ok=True)
    gates=pd.read_csv(base/'stage5a3_readiness_gates.csv') if (base/'stage5a3_readiness_gates.csv').exists() else pd.DataFrame()
    summary=pd.read_csv(base/'stage5a3_replication_lock_summary.csv') if (base/'stage5a3_replication_lock_summary.csv').exists() else pd.DataFrame()
    route='stage5a3_missing_outputs'; passed=False
    if len(gates):
        rv=gates[gates.gate=='route']; route=str(rv.value.iloc[0]) if len(rv) else route
        pv=gates[gates.gate=='stage5a3_passed']; passed=str(pv.value.iloc[0]).lower()=='true' if len(pv) else False
    rows=[]
    if len(summary):
        for _,r in summary.iterrows():
            rows.append({'block':r.block,'n_traj':int(r.n_traj),'mean_fixed_effect_db':float(r.mean_fixed_effect_db),'t_ci_low':float(r.t_ci_low),'t_ci_high':float(r.t_ci_high),'bootstrap_ci_low':float(r.bootstrap_ci_low),'bootstrap_ci_high':float(r.bootstrap_ci_high),'trajectory_fraction':float(r.trajectory_fraction),'negative_seed_fraction':float(r.negative_seed_fraction),'nested_effect_stable':bool(r.nested_effect_stable)})
    pd.DataFrame(rows).to_csv(out/'stage5a3_decision_table.csv',index=False)
    (out/'stage5a3_decision.json').write_text(json.dumps({'stage':'stage5a3_final_replication_lock','route':route,'passed':passed,'publication_claim_allowed':False,'stage5b_design_review_allowed':bool(passed),'note':'Stage 5A3 locks the 3x3x2 target-shape replication at ntraj=128 before any mechanism decomposition.'},indent=2))
    print(f'stage5a3 decision wrote {out}; route={route}')
if __name__=='__main__': main()
