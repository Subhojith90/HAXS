#!/usr/bin/env python
import argparse, json
from pathlib import Path
import pandas as pd
from stage3_common import ROOT, ensure_dir, save_json, save_dataframe
ap=argparse.ArgumentParser(); ap.add_argument('--results',default='results/stage3_lite'); ap.add_argument('--out',default='results/stage3_lite/decision'); args=ap.parse_args()
res=ROOT/args.results; out=ensure_dir(ROOT/args.out)
mechanism_score=0.0; constructive_score=0.0; scaling_score=0.0
notes=[]
mi=res/'mechanism_inference/mechanism_pairwise_inference.csv'
if mi.exists():
    df=pd.read_csv(mi)
    if len(df):
        pass_rate=((df['ci_excludes_zero']==True)&(df['welch_significant_0p05']==True)).mean()
        effect=(df['cohens_d'].abs().fillna(0).clip(upper=2)/2).mean()
        mechanism_score=float(0.6*pass_rate+0.4*effect)
        notes.append(f'mechanism pairs={len(df)} pass_rate={pass_rate:.3f}')
cv=res/'crossval_inference/crossval_publication_summary.csv'
if cv.exists():
    s=pd.read_csv(cv).iloc[0]
    mean=float(s['mean']); lo=float(s['ci_low'])
    constructive_score=max(0.0, min(1.0, mean/3.0))*0.6 + (0.4 if lo>0 else 0.0)
    constructive_score=float(min(1.0,constructive_score)); notes.append(f'crossval mean={mean:.3f} ci_low={lo:.3f}')
fs=res/'finite_size/finite_size_summary.csv'
if fs.exists():
    f=pd.read_csv(fs); scaling_score=float(min(1.0, len(f)/8.0)); notes.append(f'finite_size_groups={len(f)}')
if mechanism_score>=0.70 and scaling_score>=0.60:
    route='mechanism_publication_candidate'
elif constructive_score>=0.70:
    route='constructive_publication_candidate'
elif mechanism_score>=0.40:
    route='mechanism_needs_full_scale'
else:
    route='insufficient_evidence_more_runs_required'
dec={'route':route,'mechanism_score':mechanism_score,'constructive_score':constructive_score,'scaling_score':scaling_score,'notes':notes,'claim_guardrails':['Do not claim a no-go theorem from empirical surrogate results.','Do not claim robust 3 dB recovery unless cross-validation CI clears 3 dB.','Do not claim quantum mobile-hole dynamics; the current engine uses stochastic surrogate holes.']}
save_json(out/'stage3_decision.json',dec); save_dataframe(out/'stage3_decision_table.csv',pd.DataFrame([dec]),{})
print(f'stage3 decision wrote {out}; route={route}')
