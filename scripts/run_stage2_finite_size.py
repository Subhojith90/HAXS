#!/usr/bin/env python
import argparse, pandas as pd
from stage2_common import ROOT, load_raw_config, seed_list, dtwa_best_for_shape, summary_with_ci
from haxs.io.result_store import ensure_dir, save_dataframe, save_json

ap=argparse.ArgumentParser(); ap.add_argument('--config', default='configs/stage2_lite/finite_size.yaml'); ap.add_argument('--out', default='results/stage2_lite/finite_size'); args=ap.parse_args()
raw=load_raw_config(args.config); out=ensure_dir(ROOT/args.out); stage2=raw.get('stage2',{})
seeds=seed_list(stage2); frames=[]
for shape in stage2.get('shapes', [[6],[8],[3,3]]):
    frames.append(dtwa_best_for_shape(raw, shape, seeds))
df=pd.concat(frames, ignore_index=True)
summary=summary_with_ci(df, ['shape','dimension','N'], 'xi2_db_min', int(raw.get('seed',1729)), int(stage2.get('bootstrap_samples',400)))
save_dataframe(out/'finite_size_raw.csv', df, raw); save_dataframe(out/'finite_size_scaling.csv', summary, raw)
save_json(out/'finite_size_manifest.json', {'config':args.config,'shapes':stage2.get('shapes'), 'n_seeds':len(seeds)})
print(f'stage2 finite-size wrote {out}; rows={len(df)}')
