#!/usr/bin/env python
from __future__ import annotations
import argparse, sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from haxs.io.result_store import ensure_dir

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--results',default='results/stage4g_lite'); ap.add_argument('--out',default='figures/stage4g_lite')
    args=ap.parse_args(); res=ROOT/args.results; out=ensure_dir(ROOT/args.out)
    s=pd.read_csv(res/'disorder_seed_expansion/stage4g_trajectory_scaling_summary.csv')
    plt.figure(figsize=(6,4)); plt.errorbar(s['n_traj'],s['mean_fixed_effect_db'],yerr=[s['mean_fixed_effect_db']-s['t_ci_low'],s['t_ci_high']-s['mean_fixed_effect_db']],fmt='o-',capsize=4); plt.axhline(0,linestyle='--'); plt.xlabel('DTWA trajectories per run'); plt.ylabel('Fixed-time effect, static - mobile+SD (dB)'); plt.title('Stage 4G 3x3x2 fixed-time effect vs trajectory count'); plt.tight_layout(); plt.savefig(out/'stage4g_fixed_effect_vs_ntraj.png',dpi=160); plt.close()
    plt.figure(figsize=(6,4)); plt.plot(s['n_traj'],s['trajectory_fraction'],marker='o'); plt.axhline(0.5,linestyle='--'); plt.xlabel('DTWA trajectories per run'); plt.ylabel('Trajectory fraction of total variance'); plt.title('Stage 4G trajectory-noise stabilization'); plt.tight_layout(); plt.savefig(out/'stage4g_trajectory_fraction_vs_ntraj.png',dpi=160); plt.close()
    plt.figure(figsize=(6,4)); plt.plot(s['n_traj'],s['projected_pairs_for_80pct_power'],marker='o'); plt.xlabel('DTWA trajectories per run'); plt.ylabel('Projected disorder pairs for 80% power'); plt.title('Stage 4G projected Stage 5 sample size'); plt.tight_layout(); plt.savefig(out/'stage4g_power_projection.png',dpi=160); plt.close()
    print(f'stage4g figures wrote {out}')
if __name__=='__main__': main()
