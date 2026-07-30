#!/usr/bin/env python
"""Analyze Stage 5C.2C estimator-failure autopsy outputs."""
from __future__ import annotations
import argparse, json
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

def core_stats(root: Path, offsets):
    finals = pd.read_csv(root / 'stage4_finals.csv')
    d = paired_fixed(finals)
    by = d.groupby('disorder_seed').effect
    seed_mean = by.mean()
    within = by.var(ddof=1).fillna(0.0)
    reps = float(by.size().mean())
    between = float(seed_mean.var(ddof=1)) if len(seed_mean) > 1 else 0.0
    within_component = float(within.mean() / reps) if reps else 0.0
    total = between + within_component
    frac = within_component / total if total > 0 else 0.0
    lo, hi = t_ci(seed_mean.values)
    fixed = float(finals.fixed_time.dropna().iloc[0])
    curves = pd.read_csv(root / 'stage4_curves_all.csv')
    local_rows = []
    for off in offsets:
        times = np.sort(curves.time.unique())
        actual_t = float(times[np.argmin(np.abs(times - (fixed + float(off))))])
        q = curves[np.isclose(curves.time, actual_t)]
        aa = q[q.label == 'static_only'][KEYS + ['xi2_db']].rename(columns={'xi2_db':'a'})
        bb = q[q.label == 'mobile_plus_spin_density'][KEYS + ['xi2_db']].rename(columns={'xi2_db':'b'})
        dd = aa.merge(bb, on=KEYS, validate='one_to_one')
        sm = dd.assign(effect=dd.a-dd.b).groupby('disorder_seed').effect.mean()
        llo, lhi = t_ci(sm.values)
        local_rows.append({'offset': float(off), 'actual_time': actual_t, 'mean_effect_db': float(sm.mean()), 'seed_t_ci_low': llo, 'seed_t_ci_high': lhi, 'negative': bool(sm.mean() < 0 and lhi < 0)})
    seed_rows = pd.DataFrame({'disorder_seed': seed_mean.index, 'seed_mean_effect_db': seed_mean.values, 'within_seed_sd': np.sqrt(within.reindex(seed_mean.index).values), 'trajectory_reps': reps})
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
        'seed_rows': seed_rows,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', default='configs/stage5c2c_lite/estimator_autopsy_3x3x3.yaml')
    ap.add_argument('--results', default='results/stage5c2c_lite')
    ap.add_argument('--locked-primary', default=None, help='Optional override; otherwise use copied locked primary in results.')
    args = ap.parse_args()

    st = yaml.safe_load((ROOT / args.config).read_text())['stage5c2c']
    base = ROOT / args.results
    out = base / 'analysis'; out.mkdir(parents=True, exist_ok=True)
    locked = Path(args.locked_primary).resolve() if args.locked_primary else (base / 'locked_primary_3x3x3').resolve()
    if not locked.exists():
        ref = base / 'locked_primary_reference.json'
        if ref.exists():
            data = json.loads(ref.read_text())
            if data.get('copied_into_package_relative_path'):
                locked = (ROOT / data['copied_into_package_relative_path']).resolve()
    if not locked.exists():
        raise FileNotFoundError('Missing locked primary. Use --locked-primary or rerun Stage 5C.2C with copied locked primary.')

    primary = core_stats(locked, st['local_window_offsets'])
    rows, local_rows, seed_rows = [], [], []
    for cand in st['candidate_grid']:
        tag = str(cand['tag'])
        root = base / 'candidates' / tag / 'replication_campaign'
        if not root.exists():
            continue
        rep = core_stats(root, st['local_window_offsets'])
        block_delta = abs(primary['mean_effect_db'] - rep['mean_effect_db'])
        strict_fraction_pass = rep['trajectory_fraction'] < float(st['trajectory_fraction_below'])
        absolute_gate_pass = rep['nested_standard_error'] < float(st['absolute_nested_se_below'])
        sign_gate_pass = rep['mean_effect_db'] < 0 and rep['seed_t_ci_high'] < 0 and rep['negative_seed_fraction'] >= float(st['negative_seed_fraction_at_least'])
        local_pass = rep['local_window_all_negative']
        block_pass = block_delta <= float(st['block_compatibility_abs_db_below'])
        rows.append({
            'candidate': tag,
            'n_traj': int(cand['n_traj']),
            'trajectory_reps': int(cand['trajectory_reps']),
            'trajectory_seed_offset': int(cand.get('trajectory_seed_offset', 0)),
            'primary_mean_effect_db': primary['mean_effect_db'],
            'replication_mean_effect_db': rep['mean_effect_db'],
            'replication_seed_t_ci_low': rep['seed_t_ci_low'],
            'replication_seed_t_ci_high': rep['seed_t_ci_high'],
            'negative_seed_fraction': rep['negative_seed_fraction'],
            'nested_standard_error': rep['nested_standard_error'],
            'between_disorder_variance': rep['between_disorder_variance'],
            'within_trajectory_component_variance': rep['within_trajectory_component_variance'],
            'trajectory_fraction': rep['trajectory_fraction'],
            'absolute_nested_se_gate_pass': bool(absolute_gate_pass),
            'strict_fraction_gate_pass': bool(strict_fraction_pass),
            'local_window_all_negative': bool(local_pass),
            'block_delta_db': block_delta,
            'sign_gate_pass': bool(sign_gate_pass),
            'block_compatibility_pass': bool(block_pass),
            'current_strict_core_pass': bool(sign_gate_pass and local_pass and block_pass and strict_fraction_pass),
            'diagnostic_absolute_error_pass': bool(sign_gate_pass and local_pass and block_pass and absolute_gate_pass),
        })
        for lr in rep['local_rows']:
            local_rows.append({'candidate': tag, **lr})
        sr = rep['seed_rows'].copy(); sr.insert(0, 'candidate', tag); seed_rows.append(sr)
    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError('No Stage 5C.2C candidate campaigns found')
    df.to_csv(out / 'stage5c2c_candidate_autopsy_table.csv', index=False)
    pd.DataFrame(local_rows).to_csv(out / 'stage5c2c_local_window_table.csv', index=False)
    pd.concat(seed_rows, ignore_index=True).to_csv(out / 'stage5c2c_seed_effects_table.csv', index=False)
    df[['candidate','n_traj','trajectory_reps','trajectory_seed_offset','nested_standard_error','between_disorder_variance','within_trajectory_component_variance','trajectory_fraction']].to_csv(out / 'stage5c2c_variance_scaling_table.csv', index=False)

    strict_passes = df[df.current_strict_core_pass.astype(bool)]
    diagnostic_passes = df[df.diagnostic_absolute_error_pass.astype(bool)]
    selected = strict_passes.iloc[0].to_dict() if len(strict_passes) else df.iloc[-1].to_dict()
    if len(strict_passes):
        route = 'stage5c3_design_review_can_be_requested_under_existing_fraction_gate'
        reasons = ['stage5c2c_existing_fraction_gate_passed']
        stage5c3_allowed = True
    elif len(diagnostic_passes):
        route = 'supervisor_review_required_for_absolute_error_gate'
        reasons = ['absolute_nested_se_gate_passed_but_fraction_gate_not_passed']
        stage5c3_allowed = False
    else:
        route = 'stage5c2c_estimator_failure_unresolved'
        reasons = ['neither_fraction_gate_nor_absolute_error_diagnostic_gate_passed']
        stage5c3_allowed = False
    payload = {
        'stage': 'stage5c2c_estimator_failure_autopsy_decision',
        'stage5c3_design_review_allowed_under_existing_gate': stage5c3_allowed,
        'stage5d_broad_compute_allowed': False,
        'route': route,
        'selected_candidate': selected,
        'reasons': reasons,
        'claim_scope': 'Estimator autopsy only. Stage 5D, broad finite-size, publication, exact-hole, component-mechanism, and recovery claims remain blocked.',
    }
    (out / 'stage5c2c_decision.json').write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))

if __name__ == '__main__':
    main()
