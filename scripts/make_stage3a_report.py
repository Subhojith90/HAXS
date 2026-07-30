#!/usr/bin/env python
from __future__ import annotations
import argparse, json
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--results',default='results/stage3a_lite'); ap.add_argument('--figures',default='figures/stage3a_lite'); ap.add_argument('--out',default='manuscript/stage3a_lite'); args=ap.parse_args()
    r=ROOT/args.results; out=ROOT/args.out; out.mkdir(parents=True,exist_ok=True)
    decision=json.loads((r/'decision/stage3a_decision.json').read_text()) if (r/'decision/stage3a_decision.json').exists() else {}
    val=pd.read_csv(r/'dtwa_validation/dtwa_validation_summary.csv')
    lines=['# HAXS Stage 3A DTWA Validation Repair Report','',f"**Automated route:** `{decision.get('route','unknown')}`",'', '## DTWA validation gates','']
    lines.append(val[['gate','value','target','passed']].to_markdown(index=False))
    if (r/'paired_mechanism/paired_mechanism_inference.csv').exists():
        p=pd.read_csv(r/'paired_mechanism/paired_mechanism_inference.csv')
        lines += ['', '## Paired mechanism rerun', '', p[['group_a','group_b','n_pairs','paired_mean_difference_a_minus_b','bootstrap_ci_low','bootstrap_ci_high','holm_paired_t_p','ci_excludes_zero']].to_markdown(index=False)]
    lines += ['', '## Interpretation', '', 'Stage 3A is a validation-repair checkpoint. Full-scale mechanism validation is still forbidden unless the DTWA gates pass and the repaired-lite mechanism signal survives paired inference.', '', '## Generated figures', '', '- `dtwa_spin_length_validation.png`', '- `paired_mechanism_differences.png`']
    (out/'stage3a_report.md').write_text('\n'.join(lines), encoding='utf-8')
    print(f'stage3a report wrote {out/"stage3a_report.md"}')
if __name__=='__main__': main()
