#!/usr/bin/env python
"""Analyse C.2 holdouts with core-only corrected nested and local gates."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np, pandas as pd, yaml
ROOT=Path(__file__).resolve().parents[1]
KEYS=['family','shape','dimension','N','disorder_seed','trajectory_rep','run_seed','config_hash']
def t_ci(x):
 x=np.asarray(x,float);m=float(x.mean());n=x.size
 if n<2:return m,m
 crit={2:12.706,3:4.303,4:3.182,5:2.776,6:2.571,7:2.447,8:2.365,9:2.306,10:2.262}.get(n,1.96);h=crit*x.std(ddof=1)/np.sqrt(n);return m-h,m+h
def paired(finals):
 a=finals[finals.label=='static_only'][KEYS+['xi2_db_fixed']].rename(columns={'xi2_db_fixed':'a'});b=finals[finals.label=='mobile_plus_spin_density'][KEYS+['xi2_db_fixed']].rename(columns={'xi2_db_fixed':'b'});d=a.merge(b,on=KEYS,validate='one_to_one');d['effect']=d.a-d.b;return d
def main():
 p=argparse.ArgumentParser();p.add_argument('--config',default='configs/stage5c1_c2_lite/conditional_pipeline.yaml');p.add_argument('--results',default='results/stage5c1_c2_lite');a=p.parse_args();st=yaml.safe_load((ROOT/a.config).read_text())['stage5c1_c2'];base=ROOT/a.results/'stage5c2_holdout_preflight';rows=[]
 for shape in st['holdout_shapes']:
  name='x'.join(map(str,shape));byblock={}
  for block in ['primary','replication']:
   root=base/f'{name}_{block}_campaign';f=pd.read_csv(root/'stage4_finals.csv');d=paired(f);s=d.groupby('disorder_seed').effect;mean=s.mean();within=s.var(ddof=1).fillna(0);between=float(mean.var(ddof=1));r=float(s.size().mean());within_c=float(within.mean()/r);frac=within_c/(between+within_c) if between+within_c else 0.;lo,hi=t_ci(mean.values);fixed=float(f.fixed_time.dropna().iloc[0]);curves=pd.read_csv(root/'stage4_curves_all.csv');actual=[]
   for off in [-.1,0,.1]:
    ts=np.sort(curves.time.unique());t=float(ts[np.argmin(np.abs(ts-(fixed+off)))]);q=curves[np.isclose(curves.time,t)];aa=q[q.label=='static_only'][KEYS+['xi2_db']].rename(columns={'xi2_db':'a'});bb=q[q.label=='mobile_plus_spin_density'][KEYS+['xi2_db']].rename(columns={'xi2_db':'b'});dd=aa.merge(bb,on=KEYS,validate='one_to_one');sm=dd.assign(effect=dd.a-dd.b).groupby('disorder_seed').effect.mean();_,h=t_ci(sm.values);actual.append(bool(sm.mean()<0 and h<0))
   strict=bool(mean.mean()<0 and hi<0 and (mean<0).mean()>=.70 and frac<.50 and all(actual));byblock[block]=float(mean.mean());rows.append({'shape':name,'block':block,'mean_effect_db':float(mean.mean()),'seed_t_ci_low':lo,'seed_t_ci_high':hi,'trajectory_fraction':frac,'local_window_all_negative':all(actual),'strict_core_pass':strict})
  delta=abs(byblock['primary']-byblock['replication']);rows[-2]['block_delta_db']=delta;rows[-1]['block_delta_db']=delta
 df=pd.DataFrame(rows);out=base/'analysis';out.mkdir(exist_ok=True,parents=True);df.to_csv(out/'stage5c2_holdout_core_gate_table.csv',index=False)
 good=bool(df.strict_core_pass.all() and (df.block_delta_db<=float(st['block_compatibility_abs_db_below'])).all());payload={'stage':'stage5c2_holdout_preflight_decision','broad_finite_size_stage5c_allowed':False,'holdout_preflight_passed':good,'route':'prepare_stage5c_multigeometry_protocol' if good else 'holdout_preflight_not_passed','reasons':['all_holdout_core_gates_passed'] if good else ['one_or_more_holdout_core_gates_failed'],'claim_scope':'Holdout preflight only; no broad finite-size or publication claim.'};(out/'stage5c2_decision.json').write_text(json.dumps(payload,indent=2));print(json.dumps(payload,indent=2))
if __name__=='__main__':main()
