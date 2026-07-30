#!/usr/bin/env python
from pathlib import Path
import argparse, sys
import pandas as pd
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
def load(p): return pd.read_csv(p) if Path(p).exists() else pd.DataFrame()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--results',default='results/stage5a2_lite'); ap.add_argument('--out',default='figures/stage5a2_lite'); args=ap.parse_args()
    base=ROOT/args.results/'convergence_replication'; out=ROOT/args.out; out.mkdir(parents=True,exist_ok=True)
    s=load(base/'stage5a_convergence_replication_summary.csv'); conv=load(base/'stage5a_ntraj_convergence.csv')
    if len(s):
        fig,ax=plt.subplots(figsize=(6,4))
        for block,g in s.groupby('block'):
            g=g.sort_values('n_traj'); ax.errorbar(g.n_traj,g.mean_fixed_effect_db,yerr=[g.mean_fixed_effect_db-g.t_ci_low,g.t_ci_high-g.mean_fixed_effect_db],marker='o',label=block)
        ax.axhline(0,color='k',lw=1); ax.set_xlabel('DTWA trajectories per run'); ax.set_ylabel('fixed-time effect dB'); ax.set_title('Stage 5A2 convergence/replication'); ax.legend(); fig.tight_layout(); fig.savefig(out/'stage5a2_effect_vs_ntraj.png',dpi=180); plt.close(fig)
        fig,ax=plt.subplots(figsize=(6,4))
        for block,g in s.groupby('block'):
            g=g.sort_values('n_traj'); ax.plot(g.n_traj,g.trajectory_fraction,marker='o',label=block)
        ax.axhline(0.5,color='k',lw=1,ls='--'); ax.set_xlabel('DTWA trajectories per run'); ax.set_ylabel('trajectory variance fraction'); ax.set_title('Trajectory uncertainty convergence'); ax.legend(); fig.tight_layout(); fig.savefig(out/'stage5a2_trajectory_fraction.png',dpi=180); plt.close(fig)
    if len(conv):
        fig,ax=plt.subplots(figsize=(6,4)); ax.bar(conv.block.astype(str),conv.abs_delta_db); tol=float(conv['convergence_tolerance_db'].iloc[0]) if 'convergence_tolerance_db' in conv.columns and len(conv) else 0.25
        ax.axhline(tol,color='k',lw=1,ls='--'); ax.set_ylabel('|final - previous| dB'); ax.set_title(f'Convergence delta by seed block (tol={tol:.2f} dB)'); fig.tight_layout(); fig.savefig(out/'stage5a2_convergence_delta.png',dpi=180); plt.close(fig)
    print(f'stage5a figures wrote {out}')
if __name__=='__main__': main()
