#!/usr/bin/env python
from __future__ import annotations
import argparse, sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--results',default='results/stage4d_lite'); ap.add_argument('--out',default='figures/stage4d_lite')
    args=ap.parse_args(); base=ROOT/args.results; out=ROOT/args.out; out.mkdir(parents=True,exist_ok=True)
    ready=pd.read_csv(base/'stage4d_primary_readiness_by_shape.csv')
    x=list(range(len(ready)))
    plt.figure(figsize=(7,4))
    plt.errorbar(x, ready['mean_effect_db'], yerr=[ready['mean_effect_db']-ready['t_ci_low'], ready['t_ci_high']-ready['mean_effect_db']], fmt='o', capsize=4, label='t CI over disorder pairs')
    plt.axhline(0, linestyle='--')
    plt.xticks(x, ready['shape'])
    plt.ylabel('static_only - mobile_plus_spin_density (dB)')
    plt.title('Stage 4D fixed-time primary effect')
    plt.tight_layout(); plt.savefig(out/'stage4d_fixed_time_primary_t_ci.png',dpi=180); plt.close()
    plt.figure(figsize=(7,4))
    plt.bar(ready['shape'], ready['trajectory_fraction_of_total_variance'])
    plt.axhline(0.5, linestyle='--')
    plt.ylabel('trajectory fraction of total variance')
    plt.title('Stage 4D nested uncertainty')
    plt.tight_layout(); plt.savefig(out/'stage4d_nested_uncertainty.png',dpi=180); plt.close()
    rec=pd.read_csv(base/'stage4d_recommended_stage5_design.csv')
    plt.figure(figsize=(7,4))
    plt.bar(rec['shape'], rec['recommended_next_pairs'])
    plt.ylabel('recommended disorder pairs')
    plt.title('Projected next-scale design')
    plt.tight_layout(); plt.savefig(out/'stage4d_next_scale_projection.png',dpi=180); plt.close()
    print(f'stage4d figures wrote {out}')
if __name__=='__main__': main()
