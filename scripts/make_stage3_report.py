#!/usr/bin/env python
import argparse, json
from pathlib import Path
import pandas as pd
from stage3_common import ROOT, ensure_dir
ap=argparse.ArgumentParser(); ap.add_argument('--results',default='results/stage3_lite'); ap.add_argument('--figures',default='figures/stage3_lite'); ap.add_argument('--out',default='manuscript/stage3_lite'); args=ap.parse_args()
res=ROOT/args.results; out=ensure_dir(ROOT/args.out); figs=ROOT/args.figures
lines=[]
lines.append('# HAXS Stage 3 Publication Evidence Report\n')
lines.append('This report is automatically generated from Stage 3 outputs. It is an evidence audit, not a claim of publication readiness.\n')
# decision
p=res/'decision/stage3_decision.json'
if p.exists():
    d=json.loads(p.read_text()); lines.append('## Decision\n'); lines.append(f"Route: **{d.get('route')}**\n")
    lines.append(f"Mechanism score: {d.get('mechanism_score'):.3f}\n\nConstructive score: {d.get('constructive_score'):.3f}\n\nScaling score: {d.get('scaling_score'):.3f}\n")
    lines.append('### Claim guardrails\n'); [lines.append(f'- {x}\n') for x in d.get('claim_guardrails',[])]
# summaries
for title, rel in [('Seed campaign','seed_campaign/seed_campaign_summary.csv'),('Finite-size scaling','finite_size/finite_size_summary.csv'),('Mechanism inference','mechanism_inference/mechanism_pairwise_inference.csv'),('Cross-validation','crossval_inference/crossval_publication_summary.csv')]:
    p=res/rel
    lines.append(f'\n## {title}\n')
    if p.exists():
        df=pd.read_csv(p); lines.append(df.to_markdown(index=False)); lines.append('\n')
    else:
        lines.append('Not generated in this run.\n')
lines.append('\n## Figures generated\n')
if figs.exists():
    for f in sorted(figs.glob('*.png')): lines.append(f'- {f.name}\n')
else: lines.append('No figure directory found.\n')
lines.append('\n## Final recommendation template\n')
lines.append('Proceed toward a mechanism paper only if the mechanism pairwise inference remains significant at full scale, the finite-size trend is stable, and the manuscript explicitly states that mobile holes are treated through a stochastic surrogate rather than exact quantum dynamics.\n')
(out/'stage3_report.md').write_text(''.join(lines))
print(f"stage3 report wrote {out/'stage3_report.md'}")
