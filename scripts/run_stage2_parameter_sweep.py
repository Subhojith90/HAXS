#!/usr/bin/env python
import argparse, itertools, pandas as pd
from stage2_common import ROOT, load_raw_config, seed_list, dtwa_best_for_shape, summary_with_ci
from haxs.io.result_store import ensure_dir, save_dataframe, save_json

ap=argparse.ArgumentParser(); ap.add_argument('--config', default='configs/stage2_lite/parameter_sweep.yaml'); ap.add_argument('--out', default='results/stage2_lite/parameter_sweep'); args=ap.parse_args()
raw=load_raw_config(args.config); out=ensure_dir(ROOT/args.out); st=raw.get('stage2',{}); seeds=seed_list(st); shape=raw.get('lattice',{}).get('shape',[3,3,3])
frames=[]
for jz, ph, eta, lsd in itertools.product(st.get('jz_values',[0.35]), st.get('hole_fractions',[0.18]), st.get('mobile_etas',[0.55]), st.get('lambda_sds',[0.30])):
    frames.append(dtwa_best_for_shape(raw, shape, seeds, {'jz':jz,'hole_fraction':ph,'mobile_eta':eta,'lambda_sd':lsd}))
df=pd.concat(frames, ignore_index=True)
summary=summary_with_ci(df, ['jz','hole_fraction','mobile_eta','lambda_sd'], 'xi2_db_min', int(raw.get('seed',1729)), int(st.get('bootstrap_samples',300)))
save_dataframe(out/'parameter_sweep_raw.csv', df, raw); save_dataframe(out/'parameter_sweep_summary.csv', summary, raw)
save_json(out/'parameter_sweep_manifest.json', {'grid_points': int(len(summary)), 'n_raw_rows': int(len(df))})
print(f'stage2 parameter sweep wrote {out}; rows={len(df)}')
