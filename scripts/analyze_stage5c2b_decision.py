#!/usr/bin/env python
"""Analyze Stage 5C.2B candidate campaigns against the locked 3x3x3 primary."""
from __future__ import annotations
import argparse, json, re
from pathlib import Path
import numpy as np, pandas as pd, yaml

ROOT = Path(__file__).resolve().parents[1]
KEYS = ['family','shape','dimension','N','disorder_seed','trajectory_rep','run_seed','config_hash']


def t_ci(x):
    x = np.asarray(x, float); m = float(x.mean()); n = x.size
    if n < 2: return m, m
    crit = {2:12.706,3:4.303,4:3.182,5:2.776,6:2.571,7:2.447,8:2.365,9:2.306,10:2.262}.get(n, 1.96)
    h = crit * x.std(ddof=1) / np.sqrt(n)
    return float(m-h), float(m+h)


def paired_fixed(finals):
    a = finals[finals.label == 'static_only'][KEYS + ['xi2_db_fixed']].rename(columns={'xi2_db_fixed':'a'})
    b = finals[finals.label == 'mobile_plus_spin_density'][KEYS + ['xi2_db_fixed']].rename(columns={'xi2_db_fixed':'b'})
    d = a.merge(b, on=KEYS, validate='one_to_one')
    d['effect'] = d.a - d.b
    return d


def core_stats_from_campaign(root: Path, st: dict) -> dict:
    finals = pd.read_csv(root / 'stage4_finals.csv')
    d = paired_fixed(finals)
    s = d.groupby('disorder_seed').effect
    seed_mean = s.mean()
    within = s.var(ddof=1).fillna(0.0)
    between = float(seed_mean.var(ddof=1)) if len(seed_mean) > 1 else 0.0
    reps = float(s.size().mean())
    within_component = float(within.mean() / reps) if reps else 0.0
    total = between + within_component
    frac = within_component / total if total > 0 else 0.0
    lo, hi = t_ci(seed_mean.values)
    fixed = float(finals.fixed_time.dropna().iloc[0]) if 'fixed_time' in finals.columns else np.nan

    curves = pd.read_csv(root / 'stage4_curves_all.csv')
    local_rows = []
    for off in st['local_window_offsets']:
        times = np.sort(curves.time.unique())
        actual_t = float(times[np.argmin(np.abs(times - (fixed + float(off))))])
        q = curves[np.isclose(curves.time, actual_t)]
        aa = q[q.label == 'static_only'][KEYS + ['xi2_db']].rename(columns={'xi2_db':'a'})
        bb = q[q.label == 'mobile_plus_spin_density'][KEYS + ['xi2_db']].rename(columns={'xi2_db':'b'})
        dd = aa.merge(bb, on=KEYS, validate='one_to_one')
        sm = dd.assign(effect=dd.a-dd.b).groupby('disorder_seed').effect.mean()
        llo, lhi = t_ci(sm.values)
        local_rows.append({'offset': float(off), 'actual_time': actual_t, 'mean_effect_db': float(sm.mean()), 'seed_t_ci_low': llo, 'seed_t_ci_high': lhi, 'negative': bool(sm.mean() < 0 and lhi < 0)})

    return {
        'mean_effect_db': float(seed_mean.mean()),
        'seed_t_ci_low': lo,
        'seed_t_ci_high': hi,
        'negative_seed_fraction': float((seed_mean < 0).mean()),
        'between_disorder_variance': between,
        'mean_within_trajectory_variance': float(within.mean()),
        'within_trajectory_component_variance': within_component,
        'nested_total_variance': total,
        'nested_standard_error': float(np.sqrt(total / len(seed_mean))) if len(seed_mean) else np.nan,
        'trajectory_fraction': frac,
        'local_window_all_negative': bool(all(r['negative'] for r in local_rows)),
        'local_rows': local_rows,
    }


def parse_candidate_tag(path: Path):
    m = re.search(r'ntraj(\d+)_reps(\d+)', path.as_posix())
    return (int(m.group(1)), int(m.group(2))) if m else (None, None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', default='configs/stage5c2b_lite/replication_resolution_3x3x3.yaml')
    ap.add_argument('--results', default='results/stage5c2b_lite')
    ap.add_argument('--locked-primary', required=False, help='Override locked primary path; otherwise use locked_primary_reference.json')
    args = ap.parse_args()

    raw = yaml.safe_load((ROOT / args.config).read_text())
    st = raw['stage5c2b']
    base = ROOT / args.results
    if args.locked_primary:
        locked_primary = Path(args.locked_primary).resolve() if Path(args.locked_primary).is_absolute() else (ROOT / args.locked_primary).resolve()
    else:
        locked_primary = Path(json.loads((base / 'locked_primary_reference.json').read_text())['path']).resolve()
    if not locked_primary.exists():
        raise FileNotFoundError(f'Missing locked primary: {locked_primary}')

    out = base / 'analysis'; out.mkdir(parents=True, exist_ok=True)
    primary = core_stats_from_campaign(locked_primary, st)

    rows = []
    local_all = []
    for cand in sorted((base / 'candidates').glob('ntraj*_reps*/replication_campaign')):
        ntraj, reps = parse_candidate_tag(cand)
        rep = core_stats_from_campaign(cand, st)
        block_delta = abs(primary['mean_effect_db'] - rep['mean_effect_db'])
        strict = bool(
            rep['mean_effect_db'] < 0 and
            rep['seed_t_ci_high'] < 0 and
            rep['negative_seed_fraction'] >= float(st['negative_seed_fraction_at_least']) and
            rep['trajectory_fraction'] < float(st['trajectory_fraction_below']) and
            rep['local_window_all_negative'] and
            block_delta <= float(st['block_compatibility_abs_db_below'])
        )
        reasons = []
        if rep['mean_effect_db'] >= 0: reasons.append('mean_not_negative')
        if rep['seed_t_ci_high'] >= 0: reasons.append('ci_high_not_below_zero')
        if rep['negative_seed_fraction'] < float(st['negative_seed_fraction_at_least']): reasons.append('negative_seed_fraction_too_low')
        if rep['trajectory_fraction'] >= float(st['trajectory_fraction_below']): reasons.append('fail_trajectory_fraction')
        if not rep['local_window_all_negative']: reasons.append('local_window_not_all_negative')
        if block_delta > float(st['block_compatibility_abs_db_below']): reasons.append('primary_replication_block_delta_too_large')
        rows.append({
            'candidate': f'ntraj{ntraj}_reps{reps}', 'n_traj': ntraj, 'trajectory_reps': reps,
            'primary_mean_effect_db': primary['mean_effect_db'],
            'replication_mean_effect_db': rep['mean_effect_db'],
            'replication_seed_t_ci_low': rep['seed_t_ci_low'],
            'replication_seed_t_ci_high': rep['seed_t_ci_high'],
            'negative_seed_fraction': rep['negative_seed_fraction'],
            'trajectory_fraction': rep['trajectory_fraction'],
            'local_window_all_negative': rep['local_window_all_negative'],
            'block_delta_db': block_delta,
            'strict_core_pass': strict,
            'failure_reasons': 'pass' if not reasons else ';'.join(reasons),
        })
        for lr in rep['local_rows']:
            local_all.append({'candidate': f'ntraj{ntraj}_reps{reps}', **lr})

    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError('No Stage 5C.2B candidate campaigns found')
    df.to_csv(out / 'stage5c2b_candidate_gate_table.csv', index=False)
    pd.DataFrame(local_all).to_csv(out / 'stage5c2b_local_window_table.csv', index=False)

    passed = df[df.strict_core_pass.astype(bool)]
    if len(passed):
        selected = passed.iloc[0].to_dict()
        route = 'prepare_stage5c3_design_review'
        reasons = ['3x3x3_replication_core_gate_passed']
        allowed_c3 = True
    else:
        selected = df.iloc[-1].to_dict()
        route = 'stage5c2b_more_estimator_resolution_or_stop'
        reasons = ['3x3x3_replication_core_gate_not_passed']
        allowed_c3 = False

    payload = {
        'stage': 'stage5c2b_3x3x3_replication_resolution_decision',
        'stage5c3_design_review_allowed': allowed_c3,
        'stage5d_broad_compute_allowed': False,
        'route': route,
        'selected_candidate': selected,
        'reasons': reasons,
        'claim_scope': '3x3x3 replication-only variance-resolution. No broad finite-size, Stage 5D compute, or publication claim.',
    }
    (out / 'stage5c2b_decision.json').write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))

if __name__ == '__main__':
    main()
