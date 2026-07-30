#!/usr/bin/env python
import argparse
from stage3_common import ROOT, load_raw_config, stage3_seeds, dtwa_best_for_shape, bootstrap_mean_ci, ensure_dir, save_dataframe, save_json
import pandas as pd
ap=argparse.ArgumentParser(); ap.add_argument('--config',default='configs/stage3_lite/publication_evidence.yaml'); ap.add_argument('--out',default='results/stage3_lite/seed_campaign'); args=ap.parse_args()
raw=load_raw_config(args.config); out=ensure_dir(ROOT/args.out)
seeds=stage3_seeds(raw); shape=raw.get('lattice',{}).get('shape',[3,3,3])
df=dtwa_best_for_shape(raw, shape, seeds)
st=raw.get('stage3',{}); mean,lo,hi=bootstrap_mean_ci(df['xi2_db_min'], raw.get('seed',1729), st.get('bootstrap_samples',1200), st.get('ci',0.95))
summary=pd.DataFrame([{'shape':'x'.join(map(str,shape)),'N':int(df['N'].iloc[0]),'n_seeds':len(df),'mean_xi2_db_min':mean,'ci_low':lo,'ci_high':hi,'std':float(df['xi2_db_min'].std(ddof=1)),'median':float(df['xi2_db_min'].median()),'q05':float(df['xi2_db_min'].quantile(0.05)),'q95':float(df['xi2_db_min'].quantile(0.95))}])
save_dataframe(out/'seed_campaign_raw.csv',df,raw); save_dataframe(out/'seed_campaign_summary.csv',summary,raw); save_json(out/'seed_campaign_manifest.json',{'config':args.config,'n_seeds':len(seeds),'shape':shape})
print(f'stage3 seed campaign wrote {out}; rows={len(df)}')
