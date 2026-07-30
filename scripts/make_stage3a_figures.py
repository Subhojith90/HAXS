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
    ap=argparse.ArgumentParser(); ap.add_argument('--results',default='results/stage3a_lite'); ap.add_argument('--out',default='figures/stage3a_lite'); args=ap.parse_args()
    r=ROOT/args.results; out=ensure_dir(ROOT/args.out)
    val=pd.read_csv(r/'dtwa_validation/dtwa_validation_curve.csv')
    plt.figure(figsize=(6,4)); plt.plot(val['time'], val['spin_length'], marker='o'); plt.axhline(1.0, linestyle='--'); plt.axhline(1/(3**0.5), linestyle=':'); plt.xlabel('time'); plt.ylabel('normalized spin length'); plt.title('Stage 3A DTWA spin-length validation'); plt.tight_layout(); plt.savefig(out/'dtwa_spin_length_validation.png', dpi=180); plt.close()
    if (r/'paired_mechanism/paired_mechanism_inference.csv').exists():
        df=pd.read_csv(r/'paired_mechanism/paired_mechanism_inference.csv')
        labels=[a+' - '+b for a,b in zip(df.group_a,df.group_b)]
        x=df['paired_mean_difference_a_minus_b']; lo=x-df['bootstrap_ci_low']; hi=df['bootstrap_ci_high']-x
        plt.figure(figsize=(8,4.8)); plt.errorbar(x, range(len(df)), xerr=[lo,hi], fmt='o'); plt.axvline(0, linestyle='--'); plt.yticks(range(len(df)), labels); plt.xlabel('paired mean difference in xi2_db_min'); plt.title('Stage 3A paired mechanism differences'); plt.tight_layout(); plt.savefig(out/'paired_mechanism_differences.png', dpi=180); plt.close()
    print(f'stage3a figures wrote {out}')
if __name__=='__main__': main()
