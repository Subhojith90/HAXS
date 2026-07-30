#!/usr/bin/env python
from __future__ import annotations
import argparse, sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from haxs.io.result_store import ensure_dir

def savefig(path):
    plt.tight_layout(); plt.savefig(path,dpi=160); plt.close()

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--results',default='results/stage4a_lite'); ap.add_argument('--out',default='figures/stage4a_lite')
    args=ap.parse_args(); r=ROOT/args.results; out=ensure_dir(ROOT/args.out)
    diag=pd.read_csv(r/'stability_diagnosis/stage4a_shape_stability_diagnosis.csv')
    sens=pd.read_csv(r/'stability_diagnosis/stage4a_metric_sensitivity.csv')
    var=pd.read_csv(r/'stability_diagnosis/stage4a_variance_decomposition.csv')
    # fixed effects
    d=diag.sort_values('N')
    plt.figure(figsize=(7,4))
    x=range(len(d)); y=d.fixed_time_mean_effect_db; lo=y-d.fixed_time_ci_low; hi=d.fixed_time_ci_high-y
    plt.errorbar(list(x),y,yerr=[lo,hi],fmt='o',capsize=3)
    plt.axhline(0,linestyle='--',linewidth=1)
    plt.xticks(list(x),d['shape'],rotation=30,ha='right')
    plt.ylabel('Static - mobile+spin fixed-time effect (dB)')
    plt.title('Stage 4A fixed-time stability diagnosis')
    savefig(out/'stage4a_fixed_time_effect_diagnosis.png')
    # power projection
    plt.figure(figsize=(7,4))
    pp=d.projected_disorder_pairs_for_80pct_power.replace(-1,float('nan'))
    plt.bar(d['shape'],pp)
    plt.axhline(d.current_disorder_pairs.iloc[0] if len(d) else 0,linestyle='--',linewidth=1)
    plt.ylabel('Projected disorder pairs for 80% power')
    plt.title('Projected sample size from nested SE')
    plt.xticks(rotation=30,ha='right')
    savefig(out/'stage4a_power_projection.png')
    # metric sensitivity
    s=sens.sort_values('N')
    plt.figure(figsize=(7,4))
    plt.plot(s['shape'],s['fixed_effect_db'],marker='o',label='fixed-time')
    plt.plot(s['shape'],s['min_effect_db'],marker='o',label='min-time')
    plt.axhline(0,linestyle='--',linewidth=1)
    plt.ylabel('Paired effect (dB)')
    plt.title('Fixed-time vs min-time effect sensitivity')
    plt.legend(); plt.xticks(rotation=30,ha='right')
    savefig(out/'stage4a_metric_sensitivity.png')
    # variance fraction
    vf=var[var.metric=='xi2_db_fixed'].sort_values('N')
    plt.figure(figsize=(7,4))
    plt.bar(vf['shape'],vf['trajectory_fraction_of_total_variance'])
    plt.axhline(0.5,linestyle='--',linewidth=1)
    plt.ylabel('Trajectory fraction of total variance')
    plt.title('Nested uncertainty source diagnosis')
    plt.xticks(rotation=30,ha='right')
    savefig(out/'stage4a_variance_fraction.png')
    print(f'stage4a figures wrote {out}')
if __name__=='__main__': main()
