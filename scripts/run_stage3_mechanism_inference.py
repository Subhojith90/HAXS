#!/usr/bin/env python
import argparse, subprocess, sys
from pathlib import Path
import pandas as pd
from stage3_common import ROOT, load_raw_config, pairwise_inference, ensure_dir, save_dataframe, save_json
ap=argparse.ArgumentParser(); ap.add_argument('--config',default='configs/stage3_lite/publication_evidence.yaml'); ap.add_argument('--out',default='results/stage3_lite/mechanism_inference'); args=ap.parse_args()
raw=load_raw_config(args.config); out=ensure_dir(ROOT/args.out)
# Reuse the established Stage 2 mechanism engine, then add publication inference on top.
import yaml
cfg=dict(raw)
st=raw.get('stage3',{})
cfg['mechanism']={'seeds': int(st.get('mechanism_seeds', st.get('seeds', 60))), 'seed_start': int(st.get('seed_start', 30001))}
tmp=out/'_mechanism_stage2_compat.yaml'; tmp.write_text(yaml.safe_dump(cfg))
cmd=[sys.executable, str(ROOT/'scripts/run_stage2_mechanism_ablation.py'), '--config', str(tmp), '--out', args.out]
subprocess.run(cmd, check=True)
finals=pd.read_csv(out/'mechanism_ablation_finals.csv')
pairs=[tuple(x) for x in raw.get('stage3',{}).get('inference_pairs', [])] or None
inf=pairwise_inference(finals, pairs=pairs, seed=int(raw.get('seed',1729)), n_boot=int(raw.get('stage3',{}).get('bootstrap_samples',1200)), ci=float(raw.get('stage3',{}).get('ci',0.95)))
# Conservative claim gate: CI excludes zero and p<0.05 for at least one core pair.
inf['ci_excludes_zero']=~((inf['bootstrap_ci_low']<=0)&(inf['bootstrap_ci_high']>=0))
inf['welch_significant_0p05']=inf['welch_p']<0.05
save_dataframe(out/'mechanism_pairwise_inference.csv', inf, raw)
save_json(out/'mechanism_inference_manifest.json', {'config':args.config,'pairs_evaluated':len(inf),'source':'stage2_mechanism_ablation_plus_stage3_inference'})
print(f'stage3 mechanism inference wrote {out}; pairs={len(inf)}')
