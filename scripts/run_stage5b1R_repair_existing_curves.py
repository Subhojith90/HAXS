import argparse
from pathlib import Path
import numpy as np
import pandas as pd

OFFSETS = (-0.10, 0.0, 0.10)

def _t_ci(values):
    x=np.asarray(values,dtype=float); n=len(x); mean=float(x.mean())
    if n < 2: return mean, mean
    sd=float(x.std(ddof=1));
    # t critical values sufficient for the registered 8-seed lite design; normal fallback otherwise.
    crit={2:12.706,3:4.303,4:3.182,5:2.776,6:2.571,7:2.447,8:2.365,9:2.306,10:2.262}.get(n,1.96)
    half=crit*sd/(n**0.5)
    return mean-half, mean+half

def _fixed_time(finals):
    vals=finals['fixed_time'].dropna().unique()
    if len(vals)!=1:
        raise ValueError(f'Expected exactly one registered fixed_time; found {vals!r}')
    return float(vals[0])

def _nearest_time(curves, target):
    values=np.sort(curves['time'].dropna().unique())
    return float(values[np.argmin(np.abs(values-target))])

def _paired_effect_at_time(curves, actual_t):
    part=curves[np.isclose(curves['time'].astype(float), actual_t)].copy()
    keys=['family','shape','dimension','N','disorder_seed','trajectory_rep','run_seed','config_hash']
    a=part[part['label']=='static_only'][keys+['xi2_db']].rename(columns={'xi2_db':'a'})
    b=part[part['label']=='mobile_plus_spin_density'][keys+['xi2_db']].rename(columns={'xi2_db':'b'})
    paired=a.merge(b,on=keys,how='inner',validate='one_to_one')
    if paired.empty: raise ValueError('No paired static_only/mobile_plus_spin_density rows at selected time')
    paired['effect_db']=paired['a']-paired['b']
    return paired

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--input',required=True); p.add_argument('--out',required=True)
    args=p.parse_args(); inp=Path(args.input); out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    rows=[]
    for campaign,block in [('primary_campaign','primary'),('replication_campaign','replication')]:
        root=inp/campaign
        curves=pd.read_csv(root/'stage4_curves_all.csv')
        finals=pd.read_csv(root/'stage4_finals.csv')
        needed={'time','label','xi2_db','disorder_seed','trajectory_rep'}
        missing=needed-set(curves.columns)
        if missing: raise KeyError(f'{campaign} curves missing columns: {sorted(missing)}')
        fixed_t=_fixed_time(finals)
        for offset in OFFSETS:
            actual_t=_nearest_time(curves,fixed_t+offset)
            paired=_paired_effect_at_time(curves,actual_t)
            seed_effects=paired.groupby('disorder_seed',sort=True)['effect_db'].mean()
            ci_low,ci_high=_t_ci(seed_effects.values)
            rows.append({'block':block,'offset':offset,'registered_fixed_time':fixed_t,'target_time':fixed_t+offset,
                         'actual_time':actual_t,'n_seed_pairs':int(seed_effects.size),'n_paired_rows':int(len(paired)),
                         'mean_effect_db':float(seed_effects.mean()),'seed_t_ci_low':ci_low,'seed_t_ci_high':ci_high,
                         'negative_seed_fraction':float((seed_effects<0).mean()),
                         'negative':bool(seed_effects.mean()<0 and ci_high<0)})
    pd.DataFrame(rows).to_csv(out/'stage5b1R_curve_based_local_window.csv',index=False)
    print('wrote',out/'stage5b1R_curve_based_local_window.csv')
if __name__=='__main__': main()
