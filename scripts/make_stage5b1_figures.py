#!/usr/bin/env python
from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--results',default='results/stage5b1_lite'); ap.add_argument('--out',default='figures/stage5b1_lite'); args=ap.parse_args()
    res=Path(args.results); out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    table=pd.read_csv(res/'replicated_five_label/stage5b1_replicated_five_label_table.csv')
    core=table[table.contrast=='static_only_minus_mobile_plus_spin_density']
    if len(core):
        fig,ax=plt.subplots(figsize=(6,4)); ax.errorbar(core['block'], core['mean_fixed_effect_db'], yerr=[core['mean_fixed_effect_db']-core['t_ci_low'], core['t_ci_high']-core['mean_fixed_effect_db']], fmt='o'); ax.axhline(0,linestyle='--'); ax.set_ylabel('Fixed-time effect (dB)'); ax.set_title('Stage 5B1 core contrast by block'); fig.tight_layout(); fig.savefig(out/'stage5b1_core_contrast_by_block.png',dpi=160); plt.close(fig)
    comp=table[table.contrast_kind.isin(['core','component','interaction'])]
    if len(comp):
        fig,ax=plt.subplots(figsize=(8,4)); piv=comp.pivot_table(index='contrast',columns='block',values='mean_fixed_effect_db'); piv.plot(kind='bar',ax=ax); ax.axhline(0,linestyle='--'); ax.set_ylabel('Fixed-time effect (dB)'); ax.set_title('Replicated five-label contrasts'); fig.tight_layout(); fig.savefig(out/'stage5b1_five_label_contrasts.png',dpi=160); plt.close(fig)
    local=pd.read_csv(res/'replicated_five_label/stage5b1_local_fixed_time_window.csv')
    if len(local):
        fig,ax=plt.subplots(figsize=(6,4));
        for block,g in local.groupby('block'): ax.plot(g['window_offset'],g['mean_fixed_effect_db'],marker='o',label=block)
        ax.axhline(0,linestyle='--'); ax.set_xlabel('Local fixed-time window offset'); ax.set_ylabel('Effect (dB)'); ax.legend(); ax.set_title('Local fixed-time window diagnostic'); fig.tight_layout(); fig.savefig(out/'stage5b1_local_window.png',dpi=160); plt.close(fig)
    print('stage5b1 figures wrote', out)
if __name__=='__main__': main()
