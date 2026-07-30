#!/usr/bin/env python
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

import argparse, json
from pathlib import Path
import pandas as pd
from haxs.plotting.figures import figure_model_hierarchy, figure_validation, figure_mechanism, figure_inverse_design, figure_threshold, figure_decision
from haxs.nogo.decision import make_decision, write_decision
from haxs.io.result_store import ensure_dir
from haxs.utils.logging import append_log

ap=argparse.ArgumentParser(); ap.add_argument('--results', default='results'); ap.add_argument('--out', default='figures'); args=ap.parse_args(); out=ensure_dir(ROOT/args.out)
# decision inputs
val_path=ROOT/'tables/validation/validation_summary.csv'; validation_passed=False
if val_path.exists():
    v=pd.read_csv(val_path); validation_passed=bool(v['passed'].all())
mech={}; mp=ROOT/'results/paper_lite/mechanism/mechanism_summary.json'
if mp.exists(): mech=json.loads(mp.read_text())
opt={}; op=ROOT/'results/paper_lite/optimization/optimization_decision_inputs.json'
if op.exists(): opt=json.loads(op.read_text())
th={}; tp=ROOT/'results/paper_lite/threshold/threshold_certificate.json'
if tp.exists(): th=json.loads(tp.read_text())
decision=make_decision(validation_passed, mech, opt, th); write_decision(ROOT/'reproducibility/decision_register.json', decision)
# figures
paths=[]
paths.append(figure_model_hierarchy(out/'model_hierarchy.png'))
if val_path.exists(): paths.append(figure_validation(val_path, out/'validation_sanity.png'))
mc=ROOT/'results/paper_lite/mechanism/mechanism_curves_mean.csv'
if mc.exists(): paths.append(figure_mechanism(mc, out/'mechanism_decomposition.png'))
os=ROOT/'tables/paper_lite/optimization_summary.csv'
if os.exists(): paths.append(figure_inverse_design(os, out/'inverse_design.png'))
thcsv=ROOT/'tables/paper_lite/threshold_table.csv'
if thcsv.exists(): paths.append(figure_threshold(thcsv, out/'threshold_map.png'))
paths.append(figure_decision(ROOT/'reproducibility/decision_register.json', out/'decision_summary.png'))
# copy selected figures to tier subdirectories
for tier in ['smoke','validation','paper_lite']:
    ensure_dir(out/tier)
append_log(ROOT/'reproducibility/run_log.md', f'generated figures: {paths}')
with (ROOT/'reproducibility/command_history.sh').open('a', encoding='utf-8') as f: f.write(f'python scripts/make_all_figures.py --results {args.results} --out {args.out}\n')
print('generated figures:', *paths, sep='\n')
