#!/usr/bin/env python
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from haxs.io.result_store import ensure_dir

def tab(df, cols=None, n=30):
    if cols: df=df[cols]
    return df.head(n).to_markdown(index=False)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--results',default='results/stage4c_lite'); ap.add_argument('--figures',default='figures/stage4c_lite'); ap.add_argument('--out',default='manuscript/stage4c_lite')
    args=ap.parse_args(); base=ROOT/args.results; out=ensure_dir(ROOT/args.out)
    decision=json.loads((base/'decision/stage4c0_decision.json').read_text())
    dtwa=json.loads((base/'dtwa_validation/dtwa_validation_manifest.json').read_text())
    ed=json.loads((base/'ed_dtwa_gate/ed_dtwa_manifest.json').read_text())
    diag=pd.read_csv(base/'stability_diagnosis/stage4a_shape_stability_diagnosis.csv')
    nested=pd.read_csv(base/'publication_campaign/stage4_nested_uncertainty.csv')
    scaling=pd.read_csv(base/'trajectory_scaling/stage4c_trajectory_scaling_summary.csv')
    lines=[]
    lines.append('# HAXS Stage 4C0 Decision-Code Repair and Trajectory-Scaling Preflight Report\n')
    lines.append('## Executive verdict\n')
    lines.append(f"**Route:** `{decision['route']}`\n")
    lines.append('Stage 4C0 repairs the Stage 4B decision bookkeeping issue, adds regression coverage for the pandas `shape` bug, reruns the corrected Stage 4B checkpoint, and performs a trajectory-scaling preflight on the same targeted shapes. This remains a diagnostic checkpoint, not a publication claim.\n')
    lines.append('## Validation gates\n')
    lines.append(f"- DTWA gate passed: `{dtwa.get('passed')}`\n")
    lines.append(f"- First-step spin length: `{dtwa.get('spin_length_first_step')}`\n")
    lines.append(f"- ED-DTWA gate passed: `{ed.get('passed')}`\n")
    lines.append(f"- ED-DTWA xi2 dB RMSE: `{ed.get('xi2_db_rmse')}`\n")
    lines.append(f"- ED-DTWA spin-length RMSE: `{ed.get('spin_length_rmse')}`\n")
    lines.append('## Corrected decision bookkeeping\n')
    for k in ['shape_bookkeeping_clean','decision_nested_consistent','corrected_trajectory_dominated_shapes','fixed_negative_shapes','fixed_ci_shapes','promising_shapes']:
        lines.append(f"- {k}: `{decision.get(k)}`\n")
    lines.append('\n## Corrected shape-level stability\n')
    lines.append(tab(diag, ['family','shape','dimension','N','fixed_time_mean_effect_db','fixed_time_ci_low','fixed_time_ci_high','trajectory_fraction_of_total_variance','diagnosis']))
    lines.append('\n\n## Nested uncertainty\n')
    lines.append(tab(nested[nested.metric=='xi2_db_fixed'], ['shape','metric','mean_effect_db','nested_standard_error','trajectory_fraction_of_total_variance','nested_effect_stable']))
    lines.append('\n\n## Trajectory scaling preflight\n')
    lines.append(tab(scaling))
    lines.append('\n\n## Interpretation\n')
    lines.append('The previous bookkeeping bug is repaired when all physical shape labels remain real lattice labels and the trajectory-dominated count agrees with the nested uncertainty table. The trajectory-scaling pilot determines whether the mechanism signal should be scaled by increasing trajectory statistics first or whether the route should remain diagnostic/negative.\n')
    lines.append('\n## Forbidden claims\n')
    lines.append('- No publication-grade mechanism proof.\n- No robust 3D squeezing recovery.\n- No no-go theorem.\n- No exact quantum mobile-hole dynamics.\n- No broad full-scale approval from this lite preflight alone.\n')
    (out/'stage4c0_report.md').write_text('\n'.join(lines))
    print(f'stage4c report wrote {out}/stage4c0_report.md')
if __name__=='__main__': main()
