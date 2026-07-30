#!/usr/bin/env python
from __future__ import annotations
import argparse, json
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
def md_table(df,max_rows=20): return df.head(max_rows).to_markdown(index=False)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--results',default='results/stage4_lite'); ap.add_argument('--out',default='manuscript/stage4_lite')
    args=ap.parse_args(); res=ROOT/args.results; out=ROOT/args.out; out.mkdir(parents=True,exist_ok=True)
    dec=json.loads((res/'decision/stage4_decision.json').read_text()); p=pd.read_csv(res/'publication_campaign/stage4_primary_pair_effects.csv'); n=pd.read_csv(res/'publication_campaign/stage4_nested_uncertainty.csv'); fam=pd.read_csv(res/'publication_campaign/stage4_family_summary.csv')
    lines=[]
    lines += ['# HAXS Stage 4 Publication-Mechanism Campaign Report','',f"**Route:** `{dec['route']}`",'', 'This Stage 4 package is designed as a publication-evidence campaign for the mechanism route only. It does not claim constructive 3 dB recovery, no-go behavior, exact quantum mobile-hole dynamics, or experimental realism beyond the validated surrogate hierarchy.','']
    lines += ['## Validation Gates','',f"- DTWA repair gate passed: `{dec['dtwa_passed']}`",f"- ED-DTWA gate passed: `{dec['ed_dtwa_passed']}`",f"- Publication campaign gate passed: `{dec['campaign_passed']}`",'']
    lines += ['## Primary Result','',f"Mean fixed-time paired effect: `{dec['mean_fixed_primary_effect_db']}` dB",'', 'Negative values mean static-only has lower squeezing parameter than mobile-plus-spin-density.','']
    lines += ['## Fixed-Time Primary Pair Effects','',md_table(p[p.metric=='xi2_db_fixed']),'','## Nested Uncertainty','',md_table(n[n.metric=='xi2_db_fixed']),'','## Matched-Family Summary','',md_table(fam),'','## Interpretation','','If the decision route is `stage4_publication_candidate_internal_audit`, the package is suitable for supervisor/internal audit as a publication-grade mechanism-candidate evidence package. It should still be reviewed before manuscript submission.']
    (out/'stage4_report.md').write_text('\n'.join(lines))
    print(f'stage4 report wrote {out}/stage4_report.md')
if __name__=='__main__': main()
