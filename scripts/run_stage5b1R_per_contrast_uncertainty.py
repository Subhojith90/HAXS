import argparse
from pathlib import Path
import numpy as np
import pandas as pd

CONTRASTS=[
 ('static_only','mobile_plus_spin_density','core_static_minus_mobile_plus_sd'),
 ('static_only','mobile_only','component_static_minus_mobile_only'),
 ('static_only','spin_density_only','component_static_minus_spin_density_only'),
 ('mobile_only','mobile_plus_spin_density','mobile_only_minus_mobile_plus_sd'),
 ('spin_density_only','mobile_plus_spin_density','spin_density_only_minus_mobile_plus_sd'),
]
KEYS=['family','shape','dimension','N','disorder_seed','trajectory_rep','run_seed','config_hash']
def t_ci(x):
 x=np.asarray(x,dtype=float); n=x.size; m=float(x.mean())
 if n<2:return m,m
 sd=float(x.std(ddof=1)); crit={2:12.706,3:4.303,4:3.182,5:2.776,6:2.571,7:2.447,8:2.365,9:2.306,10:2.262}.get(n,1.96)
 h=crit*sd/np.sqrt(n); return m-h,m+h
def one(campaign,block):
 f=pd.read_csv(Path(campaign)/'stage4_finals.csv'); rows=[]
 missing=set(KEYS+['label','xi2_db_fixed'])-set(f.columns)
 if missing: raise KeyError(f'Missing final columns: {sorted(missing)}')
 for a,b,name in CONTRASTS:
  aa=f[f.label==a][KEYS+['xi2_db_fixed']].rename(columns={'xi2_db_fixed':'a'})
  bb=f[f.label==b][KEYS+['xi2_db_fixed']].rename(columns={'xi2_db_fixed':'b'})
  d=aa.merge(bb,on=KEYS,how='inner',validate='one_to_one'); d['effect_db']=d.a-d.b
  seed=d.groupby('disorder_seed',sort=True)['effect_db']
  seed_mean=seed.mean(); within=seed.var(ddof=1).fillna(0.0)
  nseed=len(seed_mean); reps=seed.size(); mean_reps=float(reps.mean())
  between=float(seed_mean.var(ddof=1)) if nseed>1 else 0.0
  within_mean=float(within.mean())
  nested_se=float(np.sqrt(max(0.0,between/nseed + within_mean/(nseed*mean_reps)))) if nseed else float('nan')
  lo,hi=t_ci(seed_mean.values)
  within_component=within_mean/max(mean_reps,1.0)
  total_variance=between+within_component
  traj_frac=float(within_component/total_variance) if total_variance>0 else 0.0
  reasons=[]
  if not seed_mean.mean()<0: reasons.append('fail_sign')
  if not hi<0: reasons.append('fail_seed_t_interval')
  if not float((seed_mean<0).mean())>=0.70: reasons.append('fail_seed_fraction')
  if not traj_frac<0.50: reasons.append('fail_trajectory_fraction')
  rows.append({'block':block,'contrast':name,'n_seed_pairs':int(nseed),'mean_trajectory_reps':mean_reps,
   'mean_effect_db':float(seed_mean.mean()),'seed_t_ci_low':lo,'seed_t_ci_high':hi,
   'negative_seed_fraction':float((seed_mean<0).mean()),'between_disorder_variance':between,
   'mean_within_trajectory_variance':within_mean,'within_trajectory_component_variance':within_component,
   'nested_total_variance':total_variance,'nested_standard_error':nested_se,
   'trajectory_fraction_of_total_variance':traj_frac,'strict_negative':not reasons,
   'failure_reasons':'pass' if not reasons else ';'.join(reasons)})
 return rows
def main():
 p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--out',required=True);a=p.parse_args()
 i=Path(a.input);o=Path(a.out);o.mkdir(parents=True,exist_ok=True)
 pd.DataFrame(one(i/'primary_campaign','primary')+one(i/'replication_campaign','replication')).to_csv(o/'stage5b1R_per_contrast_nested_uncertainty.csv',index=False)
 print('wrote',o/'stage5b1R_per_contrast_nested_uncertainty.csv')
if __name__=='__main__':main()
