#!/usr/bin/env python
from pathlib import Path
import argparse
import pandas as pd
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
def load(p): return pd.read_csv(p) if Path(p).exists() else pd.DataFrame()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--results',default='results/stage5a3_lite'); ap.add_argument('--out',default='figures/stage5a3_lite'); args=ap.parse_args()
    base=ROOT/args.results/'final_replication_lock'; out=ROOT/args.out; out.mkdir(parents=True,exist_ok=True)
    summ=load(base/'stage5a3_replication_lock_summary.csv'); seed=load(base/'stage5a3_seed_level_effects.csv')
    if len(summ):
        fig,ax=plt.subplots(figsize=(6,4))
        x=range(len(summ)); y=summ['mean_fixed_effect_db']; lo=summ['mean_fixed_effect_db']-summ['t_ci_low']; hi=summ['t_ci_high']-summ['mean_fixed_effect_db']
        ax.errorbar(list(x),y,yerr=[lo,hi],fmt='o',capsize=4,label='t CI')
        ax.axhline(0,linestyle='--',linewidth=1)
        ax.set_xticks(list(x),summ['block'].astype(str).tolist()); ax.set_ylabel('Fixed-time effect: static - mobile+SD (dB)')
        ax.set_title('Stage 5A3 locked-ntraj replication effect')
        ax.legend(); fig.tight_layout(); fig.savefig(out/'stage5a3_locked_effect_by_block.png',dpi=180); plt.close(fig)
        fig,ax=plt.subplots(figsize=(6,4))
        ax.bar(summ['block'].astype(str),summ['trajectory_fraction'])
        ax.axhline(0.5,linestyle='--',linewidth=1,label='trajectory threshold')
        ax.set_ylim(0, max(0.7, float(summ['trajectory_fraction'].max())+0.1)); ax.set_ylabel('Trajectory fraction of total variance')
        ax.set_title('Stage 5A3 trajectory fraction by block'); ax.legend(); fig.tight_layout(); fig.savefig(out/'stage5a3_trajectory_fraction_by_block.png',dpi=180); plt.close(fig)
    if len(seed):
        fig,ax=plt.subplots(figsize=(6,4))
        blocks=list(seed['block'].drop_duplicates())
        for i,b in enumerate(blocks):
            vals=seed[seed.block==b]['effect_fixed_db'].to_numpy(float)
            ax.scatter([i]*len(vals),vals,alpha=0.8)
            ax.hlines(vals.mean(),i-0.25,i+0.25)
        ax.axhline(0,linestyle='--',linewidth=1)
        ax.set_xticks(range(len(blocks)),blocks); ax.set_ylabel('Seed-level fixed-time effect (dB)')
        ax.set_title('Stage 5A3 seed-level replication lock'); fig.tight_layout(); fig.savefig(out/'stage5a3_seed_level_effects.png',dpi=180); plt.close(fig)
    print(f'stage5a3 figures wrote {out}')
if __name__=='__main__': main()
