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
    ap=argparse.ArgumentParser(); ap.add_argument('--results',default='results/stage3c_preflight'); ap.add_argument('--out',default='figures/stage3c_preflight')
    args=ap.parse_args(); res=ROOT/args.results; out=ensure_dir(ROOT/args.out)
    curve=pd.read_csv(res/'ed_dtwa_gate'/'ed_dtwa_curve.csv')
    plt.figure(figsize=(6,4)); plt.plot(curve.time,curve.ed_spin_length,marker='o',label='ED spin length'); plt.plot(curve.time,curve.dtwa_spin_length,marker='s',label='DTWA spin length'); plt.xlabel('Time'); plt.ylabel('Normalized spin length'); plt.title('Stage 3C ED-DTWA spin-length gate'); plt.legend(); plt.tight_layout(); plt.savefig(out/'ed_dtwa_spin_length_gate.png',dpi=180); plt.close()
    plt.figure(figsize=(6,4)); plt.plot(curve.time,curve.ed_xi2_db,marker='o',label='ED xi2 dB'); plt.plot(curve.time,curve.dtwa_xi2_db,marker='s',label='DTWA xi2 dB'); plt.xlabel('Time'); plt.ylabel('Squeezing xi2 dB'); plt.title('Stage 3C ED-DTWA squeezing gate'); plt.legend(); plt.tight_layout(); plt.savefig(out/'ed_dtwa_squeezing_gate.png',dpi=180); plt.close()
    pair=pd.read_csv(res/'fixed_time_nested'/'stage3c_fixed_time_pair_effects.csv')
    core=pair[pair.metric=='xi2_db_fixed'].sort_values('N')
    y=core.paired_mean_difference_a_minus_b; yerr=[y-core.bootstrap_ci_low, core.bootstrap_ci_high-y]
    plt.figure(figsize=(7,4)); plt.errorbar(core.N,y,yerr=yerr,fmt='o-',capsize=4); plt.axhline(0,linestyle='--',linewidth=1); plt.xlabel('Number of lattice sites N'); plt.ylabel('Fixed-time paired effect (dB)'); plt.title('Primary fixed-time core mechanism effect');
    for _,r in core.iterrows(): plt.annotate(str(r['shape']),(r.N,r.paired_mean_difference_a_minus_b),textcoords='offset points',xytext=(4,4),fontsize=8)
    plt.tight_layout(); plt.savefig(out/'fixed_time_core_effect.png',dpi=180); plt.close()
    nested=pd.read_csv(res/'fixed_time_nested'/'stage3c_nested_uncertainty.csv')
    nf=nested[nested.metric=='xi2_db_fixed'].sort_values('N')
    plt.figure(figsize=(7,4)); plt.bar(nf['shape'],nf['trajectory_fraction_of_total_variance']); plt.xticks(rotation=30,ha='right'); plt.ylabel('Trajectory fraction of variance'); plt.title('Nested trajectory/disorder uncertainty diagnostic'); plt.tight_layout(); plt.savefig(out/'nested_uncertainty_fraction.png',dpi=180); plt.close()
    print(f'stage3c figures wrote {out}')
if __name__=='__main__': main()
