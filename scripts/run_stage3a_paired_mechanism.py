#!/usr/bin/env python
from __future__ import annotations
import argparse, sys, math
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from haxs.io.result_store import ensure_dir, save_dataframe, save_json

def holm(pvals):
    p=np.asarray(pvals,dtype=float); m=len(p); order=np.argsort(p); adj=np.empty(m); running=0.0
    for rank, idx in enumerate(order, start=1):
        val=(m-rank+1)*p[idx]
        running=max(running,val)
        adj[idx]=min(running,1.0)
    return adj

def boot_ci(diffs, seed=1729, n_boot=4000, ci=0.95):
    rng=np.random.default_rng(seed); arr=np.asarray(diffs,dtype=float); arr=arr[np.isfinite(arr)]
    boots=np.array([rng.choice(arr,size=len(arr),replace=True).mean() for _ in range(n_boot)])
    a=(1-ci)/2
    return float(np.quantile(boots,a)), float(np.quantile(boots,1-a))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--mechanism-dir',default='results/stage3a_lite/mechanism_inference'); ap.add_argument('--out',default='results/stage3a_lite/paired_mechanism'); args=ap.parse_args()
    mech=ROOT/args.mechanism_dir; out=ensure_dir(ROOT/args.out)
    finals=pd.read_csv(mech/'mechanism_ablation_finals.csv')
    pairs=[('static_only','mobile_only'),('static_only','spin_density_only'),('static_only','mobile_plus_spin_density'),('mobile_only','mobile_plus_spin_density'),('spin_density_only','mobile_plus_spin_density'),('mobile_plus_spin_density','everything'),('static_only','everything')]
    rows=[]; pvals=[]
    for a,b in pairs:
        pa=finals[finals.label==a][['seed','xi2_db_min']].rename(columns={'xi2_db_min':'a'})
        pb=finals[finals.label==b][['seed','xi2_db_min']].rename(columns={'xi2_db_min':'b'})
        merged=pa.merge(pb,on='seed')
        d=(merged['a']-merged['b']).to_numpy(float)
        ci_low,ci_high=boot_ci(d)
        t=stats.ttest_1samp(d,0.0,nan_policy='omit')
        try: w=stats.wilcoxon(d)
        except Exception: w=type('obj',(),{'statistic':np.nan,'pvalue':np.nan})()
        sd=float(np.std(d,ddof=1)); dz=float(np.mean(d)/sd) if sd>0 else float('nan')
        rows.append({'group_a':a,'group_b':b,'n_pairs':len(d),'paired_mean_difference_a_minus_b':float(np.mean(d)),'bootstrap_ci_low':ci_low,'bootstrap_ci_high':ci_high,'paired_t':float(t.statistic),'paired_t_p':float(t.pvalue),'wilcoxon_stat':float(w.statistic),'wilcoxon_p':float(w.pvalue),'cohens_dz':dz,'ci_excludes_zero':not(ci_low<=0<=ci_high),'direction_note':'negative means group_a has stronger squeezing because xi2_db is lower'})
        pvals.append(float(t.pvalue))
    df=pd.DataFrame(rows); df['holm_paired_t_p']=holm(pvals); df['holm_significant_0p05']=df['holm_paired_t_p']<0.05
    save_dataframe(out/'paired_mechanism_inference.csv',df,{'stage':'stage3a','source':args.mechanism_dir})
    core=df[(df.group_a=='static_only')&(df.group_b=='mobile_plus_spin_density')].iloc[0].to_dict()
    save_json(out/'paired_mechanism_manifest.json',{'stage':'stage3a','pairs':len(df),'core_pair':core})
    print(f'stage3a paired mechanism wrote {out}; core_diff={core["paired_mean_difference_a_minus_b"]:.6f}; core_ci=[{core["bootstrap_ci_low"]:.6f},{core["bootstrap_ci_high"]:.6f}]')
if __name__=='__main__': main()
