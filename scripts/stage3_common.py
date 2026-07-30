from __future__ import annotations
from pathlib import Path
import json, sys, math, subprocess, platform
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from stage2_common import load_raw_config, seed_list, dtwa_best_for_shape
from haxs.io.result_store import ensure_dir, save_dataframe, save_json


def stage3_seeds(raw: dict) -> list[int]:
    st = raw.get('stage3', {})
    n = int(st.get('seeds', 60))
    start = int(st.get('seed_start', 30001))
    return list(range(start, start+n))


def bootstrap_mean_ci(x, seed=1729, n_boot=2000, ci=0.95):
    arr = np.asarray(x, dtype=float)
    arr = arr[np.isfinite(arr)]
    if len(arr) == 0:
        return float('nan'), float('nan'), float('nan')
    rng = np.random.default_rng(int(seed))
    boots = np.array([rng.choice(arr, size=len(arr), replace=True).mean() for _ in range(int(n_boot))])
    alpha = (1.0 - float(ci))/2.0
    return float(arr.mean()), float(np.quantile(boots, alpha)), float(np.quantile(boots, 1-alpha))


def cohens_d(a, b):
    a = np.asarray(a, dtype=float); b = np.asarray(b, dtype=float)
    a = a[np.isfinite(a)]; b = b[np.isfinite(b)]
    if len(a) < 2 or len(b) < 2:
        return float('nan')
    sa = a.var(ddof=1); sb = b.var(ddof=1)
    pooled = math.sqrt(((len(a)-1)*sa + (len(b)-1)*sb) / max(len(a)+len(b)-2, 1))
    return float((a.mean() - b.mean()) / pooled) if pooled > 0 else float('nan')


def pairwise_inference(df, group_col='label', value_col='xi2_db_min', pairs=None, seed=1729, n_boot=2000, ci=0.95):
    labels = sorted(df[group_col].dropna().unique())
    if pairs is None:
        pairs = [(labels[i], labels[j]) for i in range(len(labels)) for j in range(i+1, len(labels))]
    rows = []
    rng = np.random.default_rng(seed)
    for a, b in pairs:
        xa = df.loc[df[group_col] == a, value_col].to_numpy(dtype=float)
        xb = df.loc[df[group_col] == b, value_col].to_numpy(dtype=float)
        xa = xa[np.isfinite(xa)]; xb = xb[np.isfinite(xb)]
        if len(xa) == 0 or len(xb) == 0:
            continue
        diffs = np.array([rng.choice(xa, len(xa), replace=True).mean() - rng.choice(xb, len(xb), replace=True).mean() for _ in range(int(n_boot))])
        alpha = (1-ci)/2
        try:
            welch = stats.ttest_ind(xa, xb, equal_var=False, nan_policy='omit')
            mw = stats.mannwhitneyu(xa, xb, alternative='two-sided')
        except Exception:
            welch = type('obj', (), {'statistic': np.nan, 'pvalue': np.nan})()
            mw = type('obj', (), {'statistic': np.nan, 'pvalue': np.nan})()
        rows.append({
            'group_a': a, 'group_b': b, 'n_a': len(xa), 'n_b': len(xb),
            'mean_a': float(xa.mean()), 'mean_b': float(xb.mean()),
            'mean_difference_a_minus_b': float(xa.mean()-xb.mean()),
            'bootstrap_ci_low': float(np.quantile(diffs, alpha)),
            'bootstrap_ci_high': float(np.quantile(diffs, 1-alpha)),
            'welch_t': float(welch.statistic), 'welch_p': float(welch.pvalue),
            'mann_whitney_u': float(mw.statistic), 'mann_whitney_p': float(mw.pvalue),
            'cohens_d': cohens_d(xa, xb),
            'direction_note': 'negative means group_a has stronger squeezing if xi2_db is lower'
        })
    return pd.DataFrame(rows)


def write_stage3_manifest(out: Path, raw: dict, command: str, extra: dict | None = None):
    import datetime
    data = {
        'created_utc': datetime.datetime.utcnow().isoformat() + 'Z',
        'python': sys.version,
        'platform': platform.platform(),
        'command': command,
        'config_hash_payload': raw,
    }
    if extra:
        data.update(extra)
    save_json(out / 'stage3_manifest.json', data)
