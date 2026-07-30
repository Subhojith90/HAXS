#!/usr/bin/env python
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--results',default='results/stage3c_preflight'); ap.add_argument('--figures',default='figures/stage3c_preflight'); ap.add_argument('--out',default='manuscript/stage3c_preflight')
    args=ap.parse_args(); res=ROOT/args.results; out=ROOT/args.out; out.mkdir(parents=True,exist_ok=True)
    dec=json.loads((res/'decision'/'stage3c_preflight_decision.json').read_text())
    ed=json.loads((res/'ed_dtwa_gate'/'ed_dtwa_manifest.json').read_text())
    nested=json.loads((res/'fixed_time_nested'/'stage3c_fixed_time_nested_manifest.json').read_text())
    pair=pd.read_csv(res/'fixed_time_nested'/'stage3c_fixed_time_pair_effects.csv')
    fixed=pair[pair.metric=='xi2_db_fixed'].sort_values('N')
    lines=[]
    lines.append('# HAXS Stage 3C-preflight Report')
    lines.append('')
    lines.append('## Executive Verdict')
    lines.append(f"Automated route: **{dec['route']}**")
    lines.append('')
    lines.append('Stage 3C-preflight was designed as a validation-hardening gate before any full-scale Stage 3C/Stage 3D campaign. It addresses stale provenance, ED-DTWA validation, fixed-time inference, and nested trajectory/disorder uncertainty.')
    lines.append('')
    lines.append('## Validation Gates')
    lines.append(f"- ED-DTWA gate passed: **{ed['passed']}**")
    lines.append(f"- xi2 dB RMSE: `{ed['xi2_db_rmse']:.6f}`")
    lines.append(f"- spin-length RMSE: `{ed['spin_length_rmse']:.6g}`")
    lines.append(f"- DTWA first-step spin length: `{ed['dtwa_first_step_spin_length']:.6f}`")
    lines.append(f"- stale collapse findings: `{dec['stale_findings']}`")
    lines.append('')
    lines.append('## Primary Fixed-Time Mechanism Inference')
    lines.append(f"- fixed-time negative shapes: `{nested['primary_fixed_negative_shapes']}`")
    lines.append(f"- fixed-time CI-excluding-zero shapes: `{nested['primary_fixed_ci_excluding_zero_shapes']}`")
    lines.append(f"- nested-stable shapes: `{nested['nested_stable_shapes']}`")
    lines.append('')
    lines.append('| shape | N | fixed-time effect dB | 95% CI | CI excludes zero |')
    lines.append('|---|---:|---:|---|---|')
    for _,r in fixed.iterrows():
        lines.append(f"| {r['shape']} | {int(r['N'])} | {r['paired_mean_difference_a_minus_b']:.3f} | [{r['bootstrap_ci_low']:.3f}, {r['bootstrap_ci_high']:.3f}] | {bool(r['ci_excludes_zero'])} |")
    lines.append('')
    lines.append('## Interpretation')
    if dec['passed']:
        lines.append('The preflight gates passed. This supports designing a Stage 3D publication-evidence campaign, but it is still not a manuscript result by itself. Stage 3D should scale the fixed-time/nested-uncertainty protocol and preserve the clean provenance gates.')
    else:
        lines.append('The preflight gates did not all pass. Do not scale. Diagnose the failed gate before any Stage 3D design.')
    lines.append('')
    lines.append('## Figures')
    for name in ['ed_dtwa_spin_length_gate.png','ed_dtwa_squeezing_gate.png','fixed_time_core_effect.png','nested_uncertainty_fraction.png']:
        lines.append(f'- `{args.figures}/{name}`')
    (out/'stage3c_preflight_report.md').write_text('\n'.join(lines),encoding='utf-8')
    print(f'stage3c report wrote {out}/stage3c_preflight_report.md')
if __name__=='__main__': main()
