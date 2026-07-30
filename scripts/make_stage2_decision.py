#!/usr/bin/env python
from pathlib import Path
import argparse, json
import pandas as pd
from stage2_common import ROOT
from haxs.io.result_store import ensure_dir, save_json

ap=argparse.ArgumentParser(); ap.add_argument('--results', default='results/stage2_lite'); ap.add_argument('--out', default='results/stage2_lite/decision'); args=ap.parse_args()
base=ROOT/args.results; out=ensure_dir(ROOT/args.out)
summary={'route':'insufficient_evidence','constructive_score':0.0,'mechanism_score':0.0,'finite_size_score':0.0,'notes':[]}
cv=base/'cross_validation/cross_validation_summary.csv'
if cv.exists():
    df=pd.read_csv(cv); val=float(df[df['metric']=='mean_test_improvement_db']['value'].iloc[0]) if 'mean_test_improvement_db' in set(df['metric']) else 0.0
    summary['constructive_score']=val; summary['notes'].append(f'mean CV improvement dB={val:.3f}')
mech=base/'mechanism_ablation/mechanism_distances.csv'
if mech.exists():
    df=pd.read_csv(mech); mask=df['distance'].str.contains('static_only_vs_mobile_plus_spin_density|mobile_plus_spin_density_vs_static_only', regex=True)
    val=float(df[mask]['value'].max()) if mask.any() else 0.0
    summary['mechanism_score']=val; summary['notes'].append(f'static/full mechanism distance dB={val:.3f}')
fs=base/'finite_size/finite_size_scaling.csv'
if fs.exists():
    df=pd.read_csv(fs); summary['finite_size_score']=float(df['n'].min()) if len(df) else 0.0; summary['notes'].append(f'finite-size groups={len(df)}')
if summary['constructive_score']>=3.0 and summary['mechanism_score']>=0.5:
    summary['route']='constructive_candidate'
elif summary['mechanism_score']>=0.5:
    summary['route']='mechanism_candidate'
elif summary['finite_size_score']>=8:
    summary['route']='diagnostic_methods_candidate'
save_json(out/'stage2_decision.json', summary)
(out/'stage2_decision.md').write_text('# Stage 2 Decision Summary\n\n```json\n'+json.dumps(summary,indent=2)+'\n```\n', encoding='utf-8')
print(f'stage2 decision wrote {out}; route={summary["route"]}')
