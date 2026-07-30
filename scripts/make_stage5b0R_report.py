#!/usr/bin/env python
from __future__ import annotations
import argparse, sys, json
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from haxs.io.result_store import ensure_dir

def fmt(x):
    try: return f'{float(x):.3f}'
    except Exception: return str(x)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--results',default='results/stage5b0R_lite'); ap.add_argument('--figures',default='figures/stage5b0R_lite'); ap.add_argument('--out',default='manuscript/stage5b0R_lite'); args=ap.parse_args()
    res=ROOT/args.results; out=ensure_dir(ROOT/args.out)
    summ=pd.read_csv(res/'adaptive_trajectory_fraction_lock/stage5b0R_adaptive_lock_summary.csv')
    gates=pd.read_csv(res/'adaptive_trajectory_fraction_lock/stage5b0R_readiness_gates.csv')
    mech_path=res/'five_label_mechanism/stage5b0R_five_label_mechanism_table.csv'
    mech=pd.read_csv(mech_path) if mech_path.exists() else pd.DataFrame()
    route=str(gates[gates.gate=='route'].value.iloc[0]) if len(gates[gates.gate=='route']) else 'unknown'
    lock=str(gates[gates.gate=='trajectory_fraction_lock_passed'].value.iloc[0]) if len(gates[gates.gate=='trajectory_fraction_lock_passed']) else 'False'
    five_ran=str(gates[gates.gate=='five_label_mechanism_pilot_ran'].value.iloc[0]) if len(gates[gates.gate=='five_label_mechanism_pilot_ran']) else 'False'
    lines=[]
    lines.append('# Stage 5B0-R Adaptive Trajectory-Fraction Lock and Gated Five-Label Pilot')
    lines.append('')
    lines.append('## Executive summary')
    lines.append(f'- Route: `{route}`')
    lines.append(f'- Trajectory-fraction lock passed: `{lock}`')
    lines.append(f'- Five-label pilot ran: `{five_ran}`')
    lines.append('- Claim status: no publication claim; this is a targeted preflight only.')
    lines.append('')
    lines.append('## Target-shape adaptive lock')
    cols=['block','n_traj','trajectory_reps_lock','mean_fixed_effect_db','t_ci_low','t_ci_high','bootstrap_ci_low','bootstrap_ci_high','negative_seed_fraction','trajectory_fraction','stage5b0R_block_passed','failure_reasons','candidate_lock_passed']
    lines.append(summ[cols].to_markdown(index=False))
    lines.append('')
    lines.append('## Five-label mechanism pilot')
    if len(mech):
        lines.append(mech.to_markdown(index=False))
    else:
        lines.append('Five-label mechanism pilot was not executed because the trajectory-fraction lock did not pass.')
    lines.append('')
    lines.append('## Figures')
    for name in ['stage5b0R_effect_vs_ntraj.png','stage5b0R_trajectory_fraction_vs_ntraj.png','stage5b0R_seed_level_effects.png','stage5b0R_five_label_contrasts.png']:
        if (ROOT/args.figures/name).exists(): lines.append(f'![{name}](../../{args.figures}/{name})')
    lines.append('')
    lines.append('## Allowed wording')
    lines.append('Stage 5B0-R tests whether the Stage 5A3 target-shape replication signal can clear the residual trajectory-fraction gate under an adaptive locked target run. Passing this stage would justify Stage 5B design review, not publication claims.')
    (out/'stage5b0R_report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'stage5b0R report wrote {out}/stage5b0R_report.md')
if __name__=='__main__': main()
