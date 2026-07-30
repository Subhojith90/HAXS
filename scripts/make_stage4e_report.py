#!/usr/bin/env python
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from haxs.io.result_store import ensure_dir

def md_table(df):
    return df.to_markdown(index=False)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--results',default='results/stage4e_lite'); ap.add_argument('--figures',default='figures/stage4e_lite'); ap.add_argument('--out',default='manuscript/stage4e_lite')
    args=ap.parse_args(); res=ROOT/args.results; out=ensure_dir(ROOT/args.out)
    dec=json.loads((res/'decision/stage4e_decision.json').read_text())
    summ=pd.read_csv(res/'trajectory_stabilization/stage4e_trajectory_scaling_summary.csv')
    gates=pd.read_csv(res/'trajectory_stabilization/stage4e_readiness_gates.csv')
    design=pd.read_csv(res/'trajectory_stabilization/stage4e_recommended_stage5_design.csv')
    text=f'''# HAXS Stage 4E Report: 3x3x2 Trajectory Stabilization

## Executive verdict

Route: `{dec['route']}`  
Target shape: `{dec['target_shape']}`  
Publication claim allowed: **False**  
Stage 5 design-review ready: **{dec['stage5_design_review_ready']}**

Stage 4E is a trajectory-stabilization pilot for the single strongest shape from Stage 4D. It is not a final manuscript claim. The goal is to decide whether the 3x3x2 fixed-time mechanism signal survives increased trajectory statistics and whether a Stage 5 design review is justified.

## Validation stack

The DTWA repair gate and ED-DTWA gate are inherited from the Stage 4 validation stack and are executed before the Stage 4E trajectory sweep.

## Trajectory scaling summary

{md_table(summ)}

## Readiness gates

{md_table(gates)}

## Recommended Stage 5 design

{md_table(design)}

## Figures

- `stage4e_fixed_effect_vs_ntraj.png`
- `stage4e_trajectory_fraction_vs_ntraj.png`
- `stage4e_power_projection.png`

## Claims allowed

- Stage 4E is a validated surrogate trajectory-stabilization pilot for 3x3x2.
- The package reports fixed-time primary inference, seed-level t intervals, bootstrap intervals, and nested trajectory/disorder uncertainty across a trajectory-count sweep.

## Claims forbidden

- Publication-grade mechanism proof.
- Exact quantum mobile-hole dynamics.
- Robust 3D squeezing recovery.
- No-go theorem.
- Constructive 3 dB recovery.
'''
    (out/'stage4e_report.md').write_text(text)
    print(f'stage4e report wrote {out}/stage4e_report.md')
if __name__=='__main__': main()
