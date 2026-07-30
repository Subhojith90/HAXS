#!/usr/bin/env python
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from haxs.io.result_store import ensure_dir

def md_table(df,cols=None,n=20):
    if cols: df=df[cols]
    return df.head(n).to_markdown(index=False)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--results',default='results/stage4b_lite'); ap.add_argument('--figures',default='figures/stage4b_lite'); ap.add_argument('--out',default='manuscript/stage4b_lite')
    args=ap.parse_args(); base=ROOT/args.results; out=ensure_dir(ROOT/args.out)
    decision=json.loads((base/'decision/stage4b_decision.json').read_text())
    dtwa=json.loads((base/'dtwa_validation/dtwa_validation_manifest.json').read_text())
    ed=json.loads((base/'ed_dtwa_gate/ed_dtwa_manifest.json').read_text())
    diag=pd.read_csv(base/'stability_diagnosis/stage4a_shape_stability_diagnosis.csv')
    sens=pd.read_csv(base/'stability_diagnosis/stage4a_metric_sensitivity.csv')
    nested=pd.read_csv(base/'stability_diagnosis/stage4a_variance_decomposition.csv')
    lines=[]
    lines.append('# HAXS Stage 4B Targeted Mechanism Checkpoint Report\n')
    lines.append('## Executive verdict\n')
    lines.append(f"**Route:** `{decision['route']}`\n")
    lines.append('Stage 4B includes the Stage 4A seed/test fix and reruns a targeted mechanism-stability checkpoint with validation gates, fixed-time primary inference, and nested uncertainty diagnostics. It is a supervisor-checkpoint package, not a publication claim.\n')
    lines.append('## Validation gates\n')
    lines.append(f"- DTWA repair gate passed: `{dtwa.get('passed')}`\n")
    lines.append(f"- First-step spin length: `{dtwa.get('spin_length_first_step')}`\n")
    lines.append(f"- ED-DTWA gate passed: `{ed.get('passed')}`\n")
    lines.append(f"- ED-DTWA xi2 dB RMSE: `{ed.get('xi2_db_rmse')}`\n")
    lines.append(f"- ED-DTWA spin-length RMSE: `{ed.get('spin_length_rmse')}`\n")
    lines.append('## Decision metrics\n')
    for k in ['fixed_negative_shapes','fixed_ci_excluding_zero_shapes','promising_shapes','trajectory_dominated_shapes','mean_fixed_time_primary_effect_db','publication_campaign_passed']:
        lines.append(f"- {k}: `{decision.get(k)}`\n")
    lines.append('\n## Shape-level stability diagnosis\n')
    lines.append(md_table(diag,['family','shape','dimension','N','fixed_time_mean_effect_db','fixed_time_ci_low','fixed_time_ci_high','fixed_time_ci_excludes_zero','trajectory_fraction_of_total_variance','projected_disorder_pairs_for_80pct_power','diagnosis']))
    lines.append('\n\n## Fixed-time versus min-time sensitivity\n')
    lines.append(md_table(sens))
    lines.append('\n\n## Nested uncertainty summary\n')
    lines.append(md_table(nested[['shape','metric','mean_effect_db','nested_standard_error','trajectory_fraction_of_total_variance','dominant_uncertainty_source']]))
    lines.append('\n\n## Interpretation\n')
    lines.append('Stage 4B should be interpreted as a targeted checkpoint. If validation gates pass but fixed-time/nested uncertainty remains weak, the correct next step is targeted trajectory/seed scaling on the promising shapes, not broad publication writing.\n')
    (out/'stage4b_report.md').write_text('\n'.join(lines))
    print(f'stage4b report wrote {out}/stage4b_report.md')
if __name__=='__main__': main()
