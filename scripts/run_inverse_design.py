#!/usr/bin/env python
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

import argparse, yaml, json
from pathlib import Path
import pandas as pd
from haxs.optimize.splits import train_test_seeds
from haxs.optimize.objectives import evaluate_protocol, baseline_theta
from haxs.optimize.random_search import random_search
from haxs.optimize.robustness import summarize_overfitting
from haxs.io.result_store import ensure_dir, save_dataframe, save_json
from haxs.observables.diagnostics import bootstrap_ci
from haxs.utils.logging import append_log

ap=argparse.ArgumentParser(); ap.add_argument('--config', required=True); ap.add_argument('--out', default='results/paper_lite/optimization'); args=ap.parse_args(); out=ensure_dir(ROOT/args.out)
path=ROOT/args.config if not str(args.config).startswith('/') else Path(args.config)
raw=yaml.safe_load(Path(path).read_text())
opt=raw.get('optimization',{})
split=train_test_seeds(int(raw.get('seed',1729)), opt.get('n_train',3), opt.get('n_test',3))
base_theta=baseline_theta(raw.get('dtwa',{}).get('t_max',1.2))
baseline_train=evaluate_protocol(raw,base_theta,split['train']); baseline_test=evaluate_protocol(raw,base_theta,split['test'])
search=random_search(raw,split['train'],opt.get('n_candidates',10),int(raw.get('seed',1729)))
best_train=search[0]; best_test=evaluate_protocol(raw,best_train['theta'],split['test'])
gap=summarize_overfitting(best_train,best_test)
improvement=float(baseline_test['mean_xi2_db'] - best_test['mean_xi2_db'])
search_df=pd.DataFrame([{'rank':i,'objective':r['objective'],'mean_xi2_db':r['mean_xi2_db'],'mean_spin_length':r['mean_spin_length'],**r['theta']} for i,r in enumerate(search)])
save_dataframe(out/'search_results.csv', search_df, raw)
best_df=pd.DataFrame([{'label':'baseline_train',**baseline_train},{'label':'baseline_test',**baseline_test},{'label':'optimized_train',**best_train},{'label':'optimized_test',**best_test}])
# flatten object-heavy columns for csv
flat=[]
for label,res in [('baseline_train',baseline_train),('baseline_test',baseline_test),('optimized_train',best_train),('optimized_test',best_test)]:
    flat.append({'label':label,'objective':float(res['objective']),'mean_xi2':float(res['mean_xi2']),'mean_xi2_db':float(res['mean_xi2_db']),'mean_spin_length':float(res['mean_spin_length']),'theta':json.dumps(res['theta'])})
summary=pd.DataFrame(flat)
save_dataframe(out/'optimization_summary.csv', summary, raw)
ensure_dir(ROOT/'tables/paper_lite'); save_dataframe(ROOT/'tables/paper_lite/optimization_summary.csv', summary, raw)
baseline_cmp=pd.DataFrame([{'metric':'test_improvement_db_baseline_minus_optimized','value':improvement},{'metric':'overfitting_gap_db','value':gap['overfitting_gap_db']}])
save_dataframe(out/'baseline_comparison.csv', baseline_cmp, raw); save_dataframe(ROOT/'tables/paper_lite/baseline_comparison.csv', baseline_cmp, raw)
vals=[f['xi2_db_min'] for f in best_test['finals']]; mean,lo,hi=bootstrap_ci(vals, seed=raw.get('seed',1729))
unc=pd.DataFrame([{'quantity':'optimized_test_xi2_db_min','mean':mean,'ci90_low':lo,'ci90_high':hi,'n':len(vals)}])
save_dataframe(out/'uncertainty_table.csv', unc, raw); save_dataframe(ROOT/'tables/paper_lite/uncertainty_table.csv', unc, raw)
best_protocol=pd.DataFrame([{**best_train['theta'],'train_objective':best_train['objective'],'test_mean_xi2_db':best_test['mean_xi2_db'],'test_improvement_db':improvement,'overfitting_gap_db':gap['overfitting_gap_db']}])
save_dataframe(out/'best_protocol_table.csv', best_protocol, raw); save_dataframe(ROOT/'tables/paper_lite/best_protocol_table.csv', best_protocol, raw)
save_json(out/'optimization_decision_inputs.json', {'test_improvement_db':improvement,'overfitting_gap_db':gap['overfitting_gap_db'],'train_seeds':split['train'],'test_seeds':split['test'],'best_theta':best_train['theta']})
append_log(ROOT/'reproducibility/run_log.md', f'inverse design wrote {out}; improvement_db={improvement:.3f}')
with (ROOT/'reproducibility/command_history.sh').open('a', encoding='utf-8') as f: f.write(f'python scripts/run_inverse_design.py --config {args.config} --out {args.out}\n')
print(f'inverse design wrote {out}; test improvement db={improvement:.3f}')
