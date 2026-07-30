#!/usr/bin/env python
from pathlib import Path
import argparse
from stage2_common import ROOT, load_raw_config, seed_list, dtwa_best_for_shape, summary_with_ci
from haxs.io.result_store import ensure_dir, save_dataframe, save_json

ap=argparse.ArgumentParser(); ap.add_argument('--config', default='configs/stage2_lite/seed_statistics.yaml'); ap.add_argument('--out', default='results/stage2_lite/seed_statistics'); args=ap.parse_args()
raw=load_raw_config(args.config); out=ensure_dir(ROOT/args.out)
seeds=seed_list(raw.get('stage2',{})); shape=raw.get('lattice',{}).get('shape',[3,3,3])
df=dtwa_best_for_shape(raw, shape, seeds)
summary=summary_with_ci(df, ['shape','dimension','N'], 'xi2_db_min', int(raw.get('seed',1729)), int(raw.get('stage2',{}).get('bootstrap_samples',500)))
save_dataframe(out/'seed_statistics_raw.csv', df, raw); save_dataframe(out/'seed_statistics_summary.csv', summary, raw)
save_json(out/'seed_statistics_manifest.json', {'config': args.config, 'n_seeds': len(seeds), 'shape': shape})
print(f'stage2 seed statistics wrote {out}; rows={len(df)}')
