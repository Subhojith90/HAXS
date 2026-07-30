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
    ap=argparse.ArgumentParser(); ap.add_argument('--results',default='results/stage3b_lite'); ap.add_argument('--out',default='figures/stage3b_lite'); args=ap.parse_args()
    r=ROOT/args.results; out=ensure_dir(ROOT/args.out)
    eff=pd.read_csv(r/'paired_finite_size/stage3b_paired_shape_effects.csv')
    core=eff[(eff.pre_registered_core.astype(bool))&(eff.metric=='xi2_db_min')].sort_values('N')
    plt.figure(figsize=(7.2,4.4))
    if len(core):
        y=core['paired_mean_difference_a_minus_b']; x=core['N']
        yerr=[y-core['bootstrap_ci_low'], core['bootstrap_ci_high']-y]
        plt.errorbar(x,y,yerr=yerr,fmt='o-',capsize=4)
    plt.axhline(0,linestyle='--',linewidth=1)
    plt.xlabel('Number of lattice sites N')
    plt.ylabel('Paired effect: static - mobile+spin-density (dB)')
    plt.title('Stage 3B paired finite-size mechanism effect')
    plt.tight_layout(); plt.savefig(out/'paired_finite_size_core_effect.png',dpi=180); plt.close()
    finals=pd.read_csv(r/'paired_finite_size/stage3b_finals.csv')
    summ=finals.groupby(['N','dimension','label'],as_index=False)['xi2_db_min'].mean()
    plt.figure(figsize=(7.6,4.6))
    for label,g in summ.groupby('label'):
        g=g.sort_values('N')
        plt.plot(g['N'],g['xi2_db_min'],marker='o',label=label)
    plt.axhline(-3,linestyle=':',linewidth=1)
    plt.xlabel('Number of lattice sites N')
    plt.ylabel('Mean best squeezing xi2_db_min')
    plt.title('Stage 3B mechanism labels across finite sizes')
    plt.legend(fontsize=7)
    plt.tight_layout(); plt.savefig(out/'mechanism_label_finite_size_summary.png',dpi=180); plt.close()
    print(f'stage3b figures wrote {out}')
if __name__=='__main__': main()
