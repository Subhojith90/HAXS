#!/usr/bin/env python
from __future__ import annotations
import argparse, sys
from pathlib import Path
import pandas as pd, matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from haxs.io.result_store import ensure_dir

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--results',default='results/stage5b0R_lite'); ap.add_argument('--out',default='figures/stage5b0R_lite'); args=ap.parse_args()
    res=ROOT/args.results; out=ensure_dir(ROOT/args.out)
    summ=pd.read_csv(res/'adaptive_trajectory_fraction_lock/stage5b0R_adaptive_lock_summary.csv')
    seeds=pd.read_csv(res/'adaptive_trajectory_fraction_lock/stage5b0R_seed_level_effects.csv')
    mech_path=res/'five_label_mechanism/stage5b0R_five_label_mechanism_table.csv'
    mech=pd.read_csv(mech_path) if mech_path.exists() else pd.DataFrame()
    final=summ[summ.candidate_lock_passed==True]
    if len(final)==0: final=summ[summ.n_traj==summ.n_traj.max()]
    plt.figure(figsize=(7,4));
    for b,g in summ.groupby('block'):
        plt.plot(g.n_traj, g.mean_fixed_effect_db, marker='o', label=b)
    plt.axhline(0,ls='--'); plt.xlabel('ntraj'); plt.ylabel('Fixed-time effect (dB)'); plt.title('Stage 5B0-R adaptive lock effects'); plt.legend(); plt.tight_layout(); plt.savefig(out/'stage5b0R_effect_vs_ntraj.png',dpi=180); plt.close()
    plt.figure(figsize=(7,4));
    for b,g in summ.groupby('block'):
        plt.plot(g.n_traj, g.trajectory_fraction, marker='o', label=b)
    plt.axhline(0.5,ls='--'); plt.xlabel('ntraj'); plt.ylabel('Trajectory fraction'); plt.title('Adaptive trajectory-fraction gate'); plt.legend(); plt.tight_layout(); plt.savefig(out/'stage5b0R_trajectory_fraction_vs_ntraj.png',dpi=180); plt.close()
    plt.figure(figsize=(7,4));
    for b,g in seeds.groupby('block'):
        plt.scatter([b]*len(g), g.effect_fixed_db, alpha=0.75)
    plt.axhline(0,ls='--'); plt.ylabel('Seed-level fixed effect (dB)'); plt.title('Seed-level target-shape effects'); plt.tight_layout(); plt.savefig(out/'stage5b0R_seed_level_effects.png',dpi=180); plt.close()
    if len(mech):
        plt.figure(figsize=(8,4)); plt.bar(range(len(mech)), mech.mean_fixed_effect_db); plt.axhline(0,ls='--'); plt.xticks(range(len(mech)), mech.contrast, rotation=45, ha='right'); plt.ylabel('Fixed-time effect (dB)'); plt.title('Five-label mechanism pilot contrasts'); plt.tight_layout(); plt.savefig(out/'stage5b0R_five_label_contrasts.png',dpi=180); plt.close()
    print(f'stage5b0R figures wrote {out}')
if __name__=='__main__': main()
