#!/usr/bin/env python
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from haxs.io.result_store import ensure_dir

def j(path): return json.loads(Path(path).read_text())
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--results',default='results/stage4a_lite'); ap.add_argument('--figures',default='figures/stage4a_lite'); ap.add_argument('--out',default='manuscript/stage4a_lite')
    args=ap.parse_args(); r=ROOT/args.results; out=ensure_dir(ROOT/args.out)
    dec=j(r/'decision/stage4a_decision.json'); diag=j(r/'stability_diagnosis/stage4a_stability_manifest.json')
    shape=pd.read_csv(r/'stability_diagnosis/stage4a_shape_stability_diagnosis.csv')
    txt=[]
    txt.append('# HAXS Stage 4A Lite Report: Mechanism Stability Diagnosis\n')
    txt.append('## Executive Verdict\n')
    txt.append(f"Decision route: `{dec['route']}`.\n")
    txt.append('Stage 4A is a diagnostic stage, not a publication-claim stage. It investigates why the stricter Stage 4 publication gate failed under fixed-time and nested-uncertainty accounting.\n')
    txt.append('## Validation Status\n')
    txt.append(f"- DTWA validation passed: `{dec['dtwa_passed']}`\n")
    txt.append(f"- ED-DTWA validation passed: `{dec['ed_dtwa_passed']}`\n")
    txt.append(f"- Original Stage 4 publication campaign passed: `{dec['publication_campaign_passed']}`\n")
    txt.append('## Stability Diagnosis\n')
    txt.append(f"- Fixed-time negative shapes: `{diag['fixed_negative_shapes']}`\n")
    txt.append(f"- Fixed-time CI-excluding-zero shapes: `{diag['fixed_ci_shapes']}`\n")
    txt.append(f"- Promising shapes under practical/power heuristic: `{diag['promising_shapes']}`\n")
    txt.append(f"- Trajectory-dominated shapes: `{diag['trajectory_dominated_shapes']}`\n")
    txt.append(f"- Median projected disorder pairs for 80% power: `{diag['median_projected_disorder_pairs_for_80pct_power']}`\n")
    txt.append('## Shape-level Table\n')
    txt.append(shape[['shape','dimension','N','fixed_time_mean_effect_db','fixed_time_ci_low','fixed_time_ci_high','projected_disorder_pairs_for_80pct_power','diagnosis']].to_markdown(index=False))
    txt.append('\n\n## Interpretation\n')
    txt.append('The mechanism signal remains directionally useful in several shapes, but Stage 4A should be read as a failure-analysis and sample-size-design package. The next stage should be a targeted Stage 4B campaign using the shapes and uncertainty sources identified here, not a broad blind scale-up.\n')
    txt.append('## Forbidden Claims\n')
    txt.append('- No publication-grade mechanism proof yet.\n- No robust 3D squeezing recovery claim.\n- No no-go theorem.\n- No exact quantum mobile-hole claim.\n')
    (out/'stage4a_report.md').write_text('\n'.join(txt),encoding='utf-8')
    print(f'stage4a report wrote {out}/stage4a_report.md')
if __name__=='__main__': main()
