#!/usr/bin/env python
import argparse, pandas as pd
from stage2_common import ROOT, load_raw_config, dtwa_best_for_shape
from haxs.io.result_store import ensure_dir, save_dataframe, save_json

ap=argparse.ArgumentParser(); ap.add_argument('--config', default='configs/stage2_lite/runtime_scaling.yaml'); ap.add_argument('--out', default='results/stage2_lite/runtime_scaling'); args=ap.parse_args()
raw=load_raw_config(args.config); out=ensure_dir(ROOT/args.out); st=raw.get('stage2',{}); seed=int(st.get('seed',11001)); frames=[]
for shape in st.get('shapes', [[6],[8],[3,3]]): frames.append(dtwa_best_for_shape(raw, shape, [seed]))
df=pd.concat(frames, ignore_index=True); df['seconds_per_site']=df['runtime_seconds']/df['N']
save_dataframe(out/'runtime_scaling.csv', df, raw); save_json(out/'runtime_scaling_manifest.json', {'shapes':st.get('shapes'), 'seed':seed})
print(f'stage2 runtime scaling wrote {out}; rows={len(df)}')
