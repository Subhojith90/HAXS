#!/usr/bin/env python
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from haxs.io.result_store import ensure_dir

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--results',default='results/stage3b_lite'); ap.add_argument('--figures',default='figures/stage3b_lite'); ap.add_argument('--out',default='manuscript/stage3b_lite'); args=ap.parse_args()
    r=ROOT/args.results; out=ensure_dir(ROOT/args.out)
    dec=json.loads((r/'decision/stage3b_decision.json').read_text())
    val=pd.read_csv(r/'dtwa_validation/dtwa_validation_summary.csv')
    eff=pd.read_csv(r/'paired_finite_size/stage3b_paired_shape_effects.csv')
    core=eff[(eff.pre_registered_core.astype(bool))&(eff.metric=='xi2_db_min')].sort_values('N')
    dim=pd.read_csv(r/'paired_finite_size/stage3b_dimension_summary.csv')
    lines=[]
    lines.append('# HAXS Stage 3B Lite Report')
    lines.append('')
    lines.append('## Executive Verdict')
    lines.append(f"**Automated route:** `{dec.get('route')}`")
    lines.append('')
    lines.append('Stage 3B extends the repaired Stage 3A package with paired finite-size mechanism validation. It does not reopen the constructive 3 dB recovery route; the purpose is to test whether the repaired DTWA surrogate preserves a mechanism-separation signal across shapes and dimensions.')
    lines.append('')
    lines.append('## DTWA Repair Gate')
    lines.append(f"- DTWA validation passed: `{bool(val['passed'].astype(bool).all())}`")
    if 'spin_length_first_step' in val.columns:
        lines.append(f"- First-step spin length: `{float(val['spin_length_first_step'].iloc[0]):.6f}`")
    lines.append('')
    lines.append('## Core Paired Mechanism Effect')
    lines.append('Core pair: `static_only - mobile_plus_spin_density`. Negative values mean static-only is more squeezed because lower xi2_db is better.')
    lines.append('')
    lines.append(core[['shape','dimension','N','n_pairs','paired_mean_difference_a_minus_b','bootstrap_ci_low','bootstrap_ci_high','ci_excludes_zero','holm_significant_0p05']].to_markdown(index=False))
    lines.append('')
    lines.append('## Dimension Summary')
    lines.append(dim.to_markdown(index=False))
    lines.append('')
    lines.append('## Decision Summary')
    lines.append(f"- Core shapes passing CI/sign gate: `{dec.get('core_shapes_passing')}`")
    lines.append(f"- Core shapes with negative direction: `{dec.get('core_shapes_negative')}`")
    lines.append(f"- Dimension families negative: `{dec.get('dimension_families_negative')}`")
    lines.append(f"- Mean core shape effect: `{dec.get('mean_core_shape_effect_db')}` dB")
    lines.append('')
    lines.append('## Figures')
    lines.append('- `figures/stage3b_lite/paired_finite_size_core_effect.png`')
    lines.append('- `figures/stage3b_lite/mechanism_label_finite_size_summary.png`')
    lines.append('')
    lines.append('## Interpretation')
    lines.append('If the route is ready, the next supervisor-facing claim should be limited: after repairing the DTWA spin-length artifact, the lite paired finite-size surrogate continues to show a mechanism-separation signal. This is still not a constructive recovery claim, not a no-go theorem, and not an experimental-realism claim.')
    (out/'stage3b_report.md').write_text('\n'.join(lines),encoding='utf-8')
    print(f'stage3b report wrote {out/"stage3b_report.md"}')
if __name__=='__main__': main()
