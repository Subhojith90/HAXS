#!/usr/bin/env python
import argparse, pandas as pd
from stage2_common import ROOT, load_raw_config
from haxs.optimize.objectives import evaluate_protocol, baseline_theta
from haxs.optimize.random_search import random_search
from haxs.io.result_store import ensure_dir, save_dataframe, save_json

ap=argparse.ArgumentParser(); ap.add_argument('--config', default='configs/stage2_lite/cross_validation.yaml'); ap.add_argument('--out', default='results/stage2_lite/cross_validation'); args=ap.parse_args()
raw=load_raw_config(args.config); out=ensure_dir(ROOT/args.out); st=raw.get('stage2',{}); folds=int(st.get('folds',3)); spf=int(st.get('seeds_per_fold',4)); start=int(st.get('seed_start',10001)); n_cand=int(raw.get('optimization',{}).get('n_candidates',12))
rows=[]; all_seeds=list(range(start, start+folds*spf))
for k in range(folds):
    test=all_seeds[k*spf:(k+1)*spf]; train=[s for s in all_seeds if s not in test]
    base=evaluate_protocol(raw, baseline_theta(raw.get('dtwa',{}).get('t_max',1.4)), test)
    search=random_search(raw, train, n_cand, int(raw.get('seed',1729))+k)
    best=search[0]; test_eval=evaluate_protocol(raw, best['theta'], test)
    rows.append({'fold':k, 'n_train':len(train), 'n_test':len(test), 'baseline_test_xi2_db':base['mean_xi2_db'], 'optimized_test_xi2_db':test_eval['mean_xi2_db'], 'test_improvement_db':base['mean_xi2_db']-test_eval['mean_xi2_db'], 'train_objective':best['objective'], 'best_theta':str(best['theta'])})
df=pd.DataFrame(rows); summary=pd.DataFrame([{'metric':'mean_test_improvement_db','value':float(df['test_improvement_db'].mean())},{'metric':'std_test_improvement_db','value':float(df['test_improvement_db'].std(ddof=1)) if len(df)>1 else 0.0},{'metric':'n_folds','value':folds}])
save_dataframe(out/'cross_validation_folds.csv', df, raw); save_dataframe(out/'cross_validation_summary.csv', summary, raw); save_json(out/'cross_validation_manifest.json', {'folds':folds,'seeds_per_fold':spf,'n_candidates':n_cand})
print(f'stage2 cross validation wrote {out}; folds={folds}')
