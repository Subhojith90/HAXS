#!/usr/bin/env python
from __future__ import annotations
import argparse, sys, json
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from haxs.io.result_store import ensure_dir

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--results',default='results/stage5b0_lite'); ap.add_argument('--figures',default='figures/stage5b0_lite'); ap.add_argument('--out',default='manuscript/stage5b0_lite'); args=ap.parse_args()
    res=ROOT/args.results; out=ensure_dir(ROOT/args.out)
    dec=json.loads((res/'decision/stage5b0_decision.json').read_text()) if (res/'decision/stage5b0_decision.json').exists() else {}
    summ=pd.read_csv(res/'trajectory_fraction_lock/stage5b0_trajectory_lock_summary.csv')
    gates=pd.read_csv(res/'trajectory_fraction_lock/stage5b0_readiness_gates.csv')
    mech_path=res/'five_label_mechanism/stage5b0_five_label_mechanism_table.csv'
    mech=pd.read_csv(mech_path) if mech_path.exists() else pd.DataFrame()
    lines=[]
    lines.append('# Stage 5B0 / Stage 5A4: Trajectory-Fraction Lock and Five-Label Mechanism Pilot')
    lines.append('')
    lines.append(f"**Route:** `{dec.get('route','unknown')}`")
    lines.append(f"**Publication claim allowed:** `{dec.get('publication_claim_allowed',False)}`")
    lines.append(f"**Stage 5B full compute allowed by automation:** `{dec.get('stage5b_full_compute_allowed',False)}`")
    lines.append('')
    lines.append('## Purpose')
    lines.append('This stage responds to the Stage 5A3 audit: it separates Stage 4 campaign semantics from Stage 5B0 block gates, adds explicit trajectory-fraction failure reasons, reruns the locked 3x3x2 target with higher trajectory repetitions, and runs a five-label mechanism pilot only if the target lock passes.')
    lines.append('')
    lines.append('## Trajectory-fraction lock summary')
    lines.append(summ.to_markdown(index=False))
    lines.append('')
    lines.append('## Readiness gates')
    lines.append(gates.to_markdown(index=False))
    lines.append('')
    if len(mech):
        lines.append('## Five-label mechanism pilot')
        lines.append(mech.to_markdown(index=False))
        lines.append('')
    else:
        lines.append('## Five-label mechanism pilot')
        lines.append('The five-label pilot was not run because the trajectory-fraction lock did not pass.')
    lines.append('## Claims')
    lines.append('Allowed: validation gates pass for tested cases; trajectory-fraction lock and five-label pilot status are as reported. Forbidden: broad mechanism proof, finite-size scaling, constructive recovery, no-go theorem, or exact quantum mobile-hole claims.')
    (out/'stage5b0_report.md').write_text('\n'.join(lines))
    print(f'stage5b0 report wrote {out}/stage5b0_report.md')
if __name__=='__main__': main()
