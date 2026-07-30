#!/usr/bin/env python
from __future__ import annotations
import argparse, sys
from pathlib import Path
import pandas as pd, matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from haxs.io.result_store import ensure_dir

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--results',default='results/stage5b0_lite'); ap.add_argument('--out',default='figures/stage5b0_lite'); args=ap.parse_args()
    res=ROOT/args.results; out=ensure_dir(ROOT/args.out)
    summ=pd.read_csv(res/'trajectory_fraction_lock/stage5b0_trajectory_lock_summary.csv')
    seeds=pd.read_csv(res/'trajectory_fraction_lock/stage5b0_seed_level_effects.csv')
    mech_path=res/'five_label_mechanism/stage5b0_five_label_mechanism_table.csv'
    mech=pd.read_csv(mech_path) if mech_path.exists() else pd.DataFrame()
    plt.figure(figsize=(6,4)); plt.bar(summ.block, summ.mean_fixed_effect_db); plt.axhline(0,ls='--'); plt.ylabel('Fixed-time effect (dB)'); plt.title('Stage 5B0 trajectory-lock effects'); plt.tight_layout(); plt.savefig(out/'stage5b0_locked_effect_by_block.png',dpi=180); plt.close()
    plt.figure(figsize=(6,4)); plt.bar(summ.block, summ.trajectory_fraction); plt.axhline(0.5,ls='--'); plt.ylabel('Trajectory fraction'); plt.title('Trajectory-fraction gate'); plt.tight_layout(); plt.savefig(out/'stage5b0_trajectory_fraction_by_block.png',dpi=180); plt.close()
    plt.figure(figsize=(7,4));
    for b,g in seeds.groupby('block'):
        plt.scatter([b]*len(g), g.effect_fixed_db)
    plt.axhline(0,ls='--'); plt.ylabel('Seed-level fixed effect (dB)'); plt.title('Seed-level target-shape effects'); plt.tight_layout(); plt.savefig(out/'stage5b0_seed_level_effects.png',dpi=180); plt.close()
    if len(mech):
        plt.figure(figsize=(8,4)); plt.bar(range(len(mech)), mech.mean_fixed_effect_db); plt.axhline(0,ls='--'); plt.xticks(range(len(mech)), mech.contrast, rotation=45, ha='right'); plt.ylabel('Fixed-time effect (dB)'); plt.title('Five-label mechanism pilot contrasts'); plt.tight_layout(); plt.savefig(out/'stage5b0_five_label_contrasts.png',dpi=180); plt.close()
    print(f'stage5b0 figures wrote {out}')
if __name__=='__main__': main()
