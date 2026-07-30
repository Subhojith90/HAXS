#!/usr/bin/env python
from __future__ import annotations
import argparse, json
from pathlib import Path
import pandas as pd

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--results',default='results/stage5b1_lite'); ap.add_argument('--figures',default='figures/stage5b1_lite'); ap.add_argument('--out',default='manuscript/stage5b1_lite'); args=ap.parse_args()
    res=Path(args.results); out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    dec_path=res/'decision/stage5b1_decision.json'
    decision=json.loads(dec_path.read_text()) if dec_path.exists() else {'route':'missing'}
    table=pd.read_csv(res/'replicated_five_label/stage5b1_replicated_five_label_table.csv')
    core=table[table.contrast=='static_only_minus_mobile_plus_spin_density']
    lines=['# Stage 5B1 Replicated Five-Label Mechanism Decomposition Report','', '## Decision','']
    for k,v in decision.items(): lines.append(f'- {k}: `{v}`')
    lines += ['', '## Core replicated contrast', '']
    if len(core):
        lines.append(core[['block','mean_fixed_effect_db','t_ci_low','t_ci_high','negative_seed_fraction','trajectory_fraction_primary_pair','strict_contrast_passed']].to_markdown(index=False))
    lines += ['', '## Interpretation', '', 'This is a gated target-shape mechanism preflight. It may justify holdout-geometry design if the strict replicated five-label gates pass. It does not justify broad finite-size scaling or publication claims.', '', '## Claims forbidden', '', '- Publication-grade mechanism proof.','- Broad finite-size scaling.','- Exact quantum mobile-hole dynamics.','- Constructive recovery.']
    target=out/'stage5b1_report.md'; target.write_text('\n'.join(lines)+'\n')
    print('stage5b1 report wrote', target)
if __name__=='__main__': main()
