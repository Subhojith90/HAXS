#!/usr/bin/env python
"""Run Stage 5C.2B: 3x3x3 replication-only variance resolution.

This runner does not alter the locked 3x3x3 primary result. It runs only
replication candidates with pre-registered trajectory budgets and records every
attempt.
"""
from __future__ import annotations
import argparse, subprocess, sys, json
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from haxs.io.result_store import ensure_dir, save_json


def run(cmd, transcript, marker=None, dry=False):
    line = ' '.join(map(str, cmd))
    if dry:
        print('DRY RUN:', line, flush=True); transcript.append('DRY RUN: ' + line); return
    print('RUN:', line, flush=True); transcript.append('RUN: ' + line)
    if marker is not None and marker.exists():
        print('SKIP existing:', marker, flush=True); transcript.append('SKIP existing: ' + str(marker)); return
    subprocess.run([str(x) for x in cmd], cwd=ROOT, check=True)


def make_candidate_cfg(raw, st, ntraj, reps):
    return {
        'seed': raw.get('seed', 131001),
        'lattice': raw.get('lattice', {}),
        'model': raw.get('model', {}),
        'dtwa': dict(raw.get('dtwa', {}), n_traj=int(ntraj)),
        'stage4': {
            'bootstrap_samples': int(raw['stage4'].get('bootstrap_samples', 1000)),
            'ci': float(raw['stage4'].get('ci', 0.95)),
            'fixed_time_fraction': float(raw['stage4'].get('fixed_time_fraction', 0.65)),
            'trajectory_seed_stride': int(raw['stage4'].get('trajectory_seed_stride', 100000)),
            'seed_start': int(st['replication_seed_start']),
            'seeds': int(st['seeds_per_block']),
            'trajectory_reps': int(reps),
            'labels': list(st['labels']),
            'matched_families': [{'family': st['family'], 'shapes': [list(st['shape'])]}],
            'primary_pair': list(st['core_pair']),
            'gates': {
                'min_fixed_negative_shapes': 1,
                'min_fixed_ci_shapes': 1,
                'min_nested_stable_shapes': 1,
                'max_trajectory_dominated_shapes': 1,
            },
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', default='configs/stage5c2b_lite/replication_resolution_3x3x3.yaml')
    ap.add_argument('--locked-primary', required=True, help='Path to locked 3x3x3 primary_campaign from Stage 5C.2')
    ap.add_argument('--out', default='results/stage5c2b_lite')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--candidate-ntraj', nargs='*', type=int, default=None)
    ap.add_argument('--candidate-reps', nargs='*', type=int, default=None)
    ap.add_argument('--no-stop-after-first-pass', action='store_true')
    args = ap.parse_args()

    raw = yaml.safe_load((ROOT / args.config).read_text())
    st = raw['stage5c2b']
    locked = (ROOT / args.locked_primary).resolve() if not Path(args.locked_primary).is_absolute() else Path(args.locked_primary).resolve()
    if not locked.exists():
        raise FileNotFoundError(f'Missing locked 3x3x3 primary campaign: {locked}')

    ntrajs = args.candidate_ntraj or [int(x) for x in st['candidate_ntraj']]
    reps = args.candidate_reps or [int(x) for x in st['candidate_reps']]
    if len(ntrajs) != len(reps):
        raise ValueError('candidate_ntraj and candidate_reps must have the same length')

    base = ensure_dir(ROOT / args.out)
    gen = ensure_dir(base / '_generated_configs')
    cand_root = ensure_dir(base / 'candidates')
    transcript = []

    # Record locked primary provenance without copying large data.
    save_json(base / 'locked_primary_reference.json', {'path': str(locked), 'stage': 'locked_3x3x3_primary_reference'})

    for ntraj, rep in zip(ntrajs, reps):
        tag = f'ntraj{int(ntraj)}_reps{int(rep)}'
        cfg = make_candidate_cfg(raw, st, ntraj, rep)
        cfg_path = gen / f'{tag}.yaml'
        cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False))
        out = cand_root / tag / 'replication_campaign'
        cmd = [sys.executable, 'scripts/run_stage4_publication_campaign.py', '--config', str(cfg_path.relative_to(ROOT)), '--out', str(out.relative_to(ROOT))]
        run(cmd, transcript, out / 'stage4_publication_campaign_manifest.json', dry=args.dry_run)

    (base / 'COMMAND_TRANSCRIPT_STAGE5C2B.txt').write_text('\n'.join(transcript) + '\n')
    save_json(base / 'stage5c2b_run_manifest.json', {
        'stage': 'stage5c2b_3x3x3_replication_resolution',
        'locked_primary': str(locked),
        'candidate_ntraj': ntrajs,
        'candidate_reps': reps,
        'stop_after_first_pass_requested': bool(st.get('stop_after_first_pass', True) and not args.no_stop_after_first_pass),
        'dry_run': bool(args.dry_run),
    })
    print('Stage 5C.2B dry run complete.' if args.dry_run else 'Stage 5C.2B candidate campaigns complete.')

if __name__ == '__main__':
    main()
