#!/usr/bin/env python
import argparse, subprocess, sys
from pathlib import Path
import pandas as pd
from stage3_common import ROOT, load_raw_config, bootstrap_mean_ci, ensure_dir, save_dataframe, save_json
ap=argparse.ArgumentParser(); ap.add_argument('--config',default='configs/stage3_lite/publication_evidence.yaml'); ap.add_argument('--out',default='results/stage3_lite/crossval_inference'); args=ap.parse_args()
raw=load_raw_config(args.config); out=ensure_dir(ROOT/args.out)
# Build a temporary Stage2-compatible config by using stage3 fold settings; the stage2 script reads stage2.*.
import yaml, tempfile
cfg=dict(raw); cfg['stage2']={'folds':int(raw.get('stage3',{}).get('folds',5)),'seeds_per_fold':int(raw.get('stage3',{}).get('seeds_per_fold',5)),'seed_start':int(raw.get('stage3',{}).get('seed_start',30001))}
tmp=out/'_crossval_stage2_compat.yaml'; tmp.write_text(yaml.safe_dump(cfg))
cmd=[sys.executable, str(ROOT/'scripts/run_stage2_cross_validation.py'), '--config', str(tmp), '--out', args.out]
subprocess.run(cmd, check=True)
df=pd.read_csv(out/'cross_validation_folds.csv')
mean,lo,hi=bootstrap_mean_ci(df['test_improvement_db'], raw.get('seed',1729), raw.get('stage3',{}).get('bootstrap_samples',1200), raw.get('stage3',{}).get('ci',0.95))
summary=pd.DataFrame([{'metric':'test_improvement_db','n_folds':len(df),'mean':mean,'ci_low':lo,'ci_high':hi,'std':float(df['test_improvement_db'].std(ddof=1)) if len(df)>1 else 0.0,'target_3db_pass':bool(lo>=3.0),'positive_ci_pass':bool(lo>0)}])
save_dataframe(out/'crossval_publication_summary.csv',summary,raw); save_json(out/'crossval_inference_manifest.json',{'config':args.config,'folds':len(df)})
print(f'stage3 cross-validation inference wrote {out}; folds={len(df)}')
