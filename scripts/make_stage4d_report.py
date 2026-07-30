#!/usr/bin/env python
from __future__ import annotations
import argparse, json
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]

def md_table(df, max_rows=20):
    return df.head(max_rows).to_markdown(index=False)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--results',default='results/stage4d_lite'); ap.add_argument('--figures',default='figures/stage4d_lite'); ap.add_argument('--out',default='manuscript/stage4d_lite')
    args=ap.parse_args(); base=ROOT/args.results; out=ROOT/args.out; out.mkdir(parents=True,exist_ok=True)
    dec=json.loads((base/'decision/stage4d_decision.json').read_text())
    dtwa=json.loads((base/'dtwa_validation/dtwa_validation_manifest.json').read_text())
    ed=json.loads((base/'ed_dtwa_gate/ed_dtwa_manifest.json').read_text())
    ready=pd.read_csv(base/'stage4d_primary_readiness_by_shape.csv')
    rec=pd.read_csv(base/'stage4d_recommended_stage5_design.csv')
    text=f"""# HAXS Stage 4D Targeted Publication Pilot Report

## Executive verdict

**Route:** `{dec['route']}`

Stage 4D is a targeted publication-pilot checkpoint. It keeps the DTWA and ED-DTWA validation gates active, uses fixed-time inference as the primary endpoint, and evaluates whether the narrowed promising shapes are ready for a manuscript-scale run.

## Validation gates

- DTWA repair gate passed: **{dtwa.get('passed')}**
- First-step spin length: **{dtwa.get('spin_length_first_step')}**
- ED-DTWA gate passed: **{ed.get('passed')}**
- ED-DTWA xi2 dB RMSE: **{ed.get('xi2_db_rmse')}**
- ED-DTWA spin-length RMSE: **{ed.get('spin_length_rmse', ed.get('spin_rmse'))}**

## Primary fixed-time readiness by shape

{md_table(ready)}

## Recommended next-scale design

{md_table(rec)}

## Interpretation

This package should not be framed as a final publication result unless the decision route explicitly allows it. The scientifically safe interpretation is that Stage 4D tests whether the most promising geometry family from Stage 4C0 remains viable under stronger targeted statistics. Constructive recovery, no-go theorem, exact quantum mobile-hole dynamics, and experimental-realism claims remain outside scope.

## Figures

- `figures/stage4d_lite/stage4d_fixed_time_primary_t_ci.png`
- `figures/stage4d_lite/stage4d_nested_uncertainty.png`
- `figures/stage4d_lite/stage4d_next_scale_projection.png`
"""
    (out/'stage4d_report.md').write_text(text)
    print(f'stage4d report wrote {out}/stage4d_report.md')
if __name__=='__main__': main()
