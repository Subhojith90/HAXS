#!/usr/bin/env python
import argparse, pandas as pd, numpy as np
from stage3_common import ROOT, load_raw_config, stage3_seeds, dtwa_best_for_shape, bootstrap_mean_ci, ensure_dir, save_dataframe, save_json
ap=argparse.ArgumentParser(); ap.add_argument('--config',default='configs/stage3_lite/publication_evidence.yaml'); ap.add_argument('--out',default='results/stage3_lite/finite_size'); args=ap.parse_args()
raw=load_raw_config(args.config); out=ensure_dir(ROOT/args.out); st=raw.get('stage3',{})
seeds=stage3_seeds(raw); shapes=st.get('finite_size_shapes',[[2,3],[3,3],[2,2,2],[3,3,2],[3,3,3]])
raws=[]; sums=[]
for shape in shapes:
    df=dtwa_best_for_shape(raw, shape, seeds); raws.append(df)
    mean,lo,hi=bootstrap_mean_ci(df['xi2_db_min'], raw.get('seed',1729)+int(df['N'].iloc[0]), st.get('bootstrap_samples',1200), st.get('ci',0.95))
    sums.append({'shape':'x'.join(map(str,shape)),'dimension':len(shape),'N':int(df['N'].iloc[0]),'n_seeds':len(df),'mean_xi2_db_min':mean,'ci_low':lo,'ci_high':hi,'std':float(df['xi2_db_min'].std(ddof=1))})
all_df=pd.concat(raws,ignore_index=True); summary=pd.DataFrame(sums).sort_values('N')
if len(summary)>=2:
    x=np.log(summary['N'].to_numpy(dtype=float)); y=summary['mean_xi2_db_min'].to_numpy(dtype=float); slope,intercept=np.polyfit(x,y,1)
else: slope=intercept=float('nan')
trend=pd.DataFrame([{'fit':'mean_xi2_db_min_vs_logN','slope':float(slope),'intercept':float(intercept),'n_groups':len(summary)}])
save_dataframe(out/'finite_size_raw.csv',all_df,raw); save_dataframe(out/'finite_size_summary.csv',summary,raw); save_dataframe(out/'finite_size_trend.csv',trend,raw); save_json(out/'finite_size_manifest.json',{'config':args.config,'shapes':shapes,'n_seeds_per_shape':len(seeds)})
print(f'stage3 finite-size wrote {out}; rows={len(all_df)} groups={len(summary)}')
