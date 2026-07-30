#!/usr/bin/env python
import argparse
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from stage3_common import ROOT, ensure_dir
ap=argparse.ArgumentParser(); ap.add_argument('--results',default='results/stage3_lite'); ap.add_argument('--out',default='figures/stage3_lite'); args=ap.parse_args()
res=ROOT/args.results; out=ensure_dir(ROOT/args.out)
# seed distribution
p=res/'seed_campaign/seed_campaign_raw.csv'
if p.exists():
    df=pd.read_csv(p); plt.figure(); plt.hist(df['xi2_db_min'], bins=20); plt.xlabel('Best squeezing xi2_db'); plt.ylabel('count'); plt.title('Stage 3 seed campaign distribution'); plt.tight_layout(); plt.savefig(out/'seed_campaign_distribution.png', dpi=200); plt.close()
# finite size
p=res/'finite_size/finite_size_summary.csv'
if p.exists():
    df=pd.read_csv(p).sort_values('N'); plt.figure(); plt.errorbar(df['N'], df['mean_xi2_db_min'], yerr=[df['mean_xi2_db_min']-df['ci_low'], df['ci_high']-df['mean_xi2_db_min']], fmt='o-'); plt.xlabel('N'); plt.ylabel('Mean best xi2_db'); plt.title('Stage 3 finite-size trend'); plt.tight_layout(); plt.savefig(out/'finite_size_trend.png', dpi=200); plt.close()
# mechanism inference
p=res/'mechanism_inference/mechanism_pairwise_inference.csv'
if p.exists():
    df=pd.read_csv(p); labels=(df['group_a']+' vs '+df['group_b']).tolist(); y=range(len(df)); plt.figure(figsize=(8,max(3,0.5*len(df)))); plt.errorbar(df['mean_difference_a_minus_b'], y, xerr=[df['mean_difference_a_minus_b']-df['bootstrap_ci_low'], df['bootstrap_ci_high']-df['mean_difference_a_minus_b']], fmt='o'); plt.axvline(0, linestyle='--'); plt.yticks(y, labels); plt.xlabel('Mean difference in xi2_db'); plt.title('Stage 3 mechanism inference'); plt.tight_layout(); plt.savefig(out/'mechanism_pairwise_inference.png', dpi=200); plt.close()
# crossval
p=res/'crossval_inference/cross_validation_folds.csv'
if p.exists():
    df=pd.read_csv(p); plt.figure(); plt.plot(df['fold'], df['test_improvement_db'], marker='o'); plt.axhline(0, linestyle='--'); plt.axhline(3, linestyle=':'); plt.xlabel('fold'); plt.ylabel('test improvement dB'); plt.title('Stage 3 cross-validation improvement'); plt.tight_layout(); plt.savefig(out/'crossval_improvement.png', dpi=200); plt.close()
print(f'stage3 figures wrote {out}')
