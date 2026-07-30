#!/usr/bin/env python
from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--results',default='results/stage4_lite'); ap.add_argument('--out',default='figures/stage4_lite')
    args=ap.parse_args(); res=ROOT/args.results; out=ROOT/args.out; out.mkdir(parents=True,exist_ok=True)
    p=pd.read_csv(res/'publication_campaign/stage4_primary_pair_effects.csv'); q=p[p.metric=='xi2_db_fixed'].sort_values(['dimension','N'])
    plt.figure(figsize=(7,4)); plt.axhline(0,linestyle='--',linewidth=1)
    y=q.mean_effect_db; plt.errorbar(q.N,y,yerr=[y-q.bootstrap_ci_low,q.bootstrap_ci_high-y],fmt='o-')
    for _,r in q.iterrows(): plt.text(r.N,r.mean_effect_db,r.shape,fontsize=8)
    plt.xlabel('N'); plt.ylabel('fixed-time paired effect dB'); plt.title('Stage 4 primary mechanism effect'); plt.tight_layout(); plt.savefig(out/'stage4_fixed_time_primary_effect.png',dpi=180); plt.close()
    n=pd.read_csv(res/'publication_campaign/stage4_nested_uncertainty.csv'); n=n[n.metric=='xi2_db_fixed'].sort_values('N')
    plt.figure(figsize=(7,4)); plt.bar(n['shape'],n['trajectory_fraction_of_total_variance']); plt.xticks(rotation=35); plt.ylabel('trajectory variance fraction'); plt.title('Nested uncertainty contribution'); plt.tight_layout(); plt.savefig(out/'stage4_nested_uncertainty.png',dpi=180); plt.close()
    f=pd.read_csv(res/'publication_campaign/stage4_family_summary.csv')
    plt.figure(figsize=(6,4)); plt.bar(f.family,f.mean_fixed_effect_db); plt.axhline(0,linestyle='--',linewidth=1); plt.xticks(rotation=25); plt.ylabel('mean fixed effect dB'); plt.title('Matched-family mechanism summary'); plt.tight_layout(); plt.savefig(out/'stage4_family_summary.png',dpi=180); plt.close()
    print(f'stage4 figures wrote {out}')
if __name__=='__main__': main()
