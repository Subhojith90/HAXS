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
    ap=argparse.ArgumentParser(); ap.add_argument('--results',default='results/stage4c_lite'); ap.add_argument('--out',default='figures/stage4c_lite')
    args=ap.parse_args(); base=ROOT/args.results; out=ensure_dir(ROOT/args.out)
    diag=pd.read_csv(base/'stability_diagnosis/stage4a_shape_stability_diagnosis.csv')
    nested=pd.read_csv(base/'publication_campaign/stage4_nested_uncertainty.csv')
    scaling=pd.read_csv(base/'trajectory_scaling/stage4c_trajectory_scaling_summary.csv')
    # fixed effects
    plt.figure(figsize=(7,4)); d=diag.sort_values('N')
    plt.errorbar(d['shape'], d['fixed_time_mean_effect_db'], yerr=[d['fixed_time_mean_effect_db']-d['fixed_time_ci_low'], d['fixed_time_ci_high']-d['fixed_time_mean_effect_db']], fmt='o', capsize=4)
    plt.axhline(0, linestyle='--'); plt.ylabel('static - mobile+spin-density (dB)'); plt.title('Stage 4C0 corrected fixed-time effects'); plt.tight_layout(); plt.savefig(out/'stage4c_corrected_fixed_time_effects.png',dpi=180); plt.close()
    # trajectory fraction
    nf=nested[nested.metric=='xi2_db_fixed'].sort_values('N')
    plt.figure(figsize=(7,4)); plt.bar(nf['shape'], nf['trajectory_fraction_of_total_variance']); plt.axhline(0.5, linestyle='--'); plt.ylim(0,1); plt.ylabel('trajectory fraction of variance'); plt.title('Corrected trajectory-dominated uncertainty check'); plt.tight_layout(); plt.savefig(out/'stage4c_corrected_trajectory_fraction.png',dpi=180); plt.close()
    # scaling
    plt.figure(figsize=(7,4)); plt.plot(scaling['n_traj'], scaling['trajectory_dominated_shapes'], marker='o', label='trajectory dominated shapes'); plt.plot(scaling['n_traj'], scaling['fixed_negative_shapes'], marker='o', label='fixed negative shapes'); plt.xlabel('n_traj per run'); plt.ylabel('count'); plt.title('Trajectory-scaling preflight summary'); plt.legend(); plt.tight_layout(); plt.savefig(out/'stage4c_trajectory_scaling_summary.png',dpi=180); plt.close()
    print(f'stage4c figures wrote {out}')
if __name__=='__main__': main()
