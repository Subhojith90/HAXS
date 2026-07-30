#!/usr/bin/env python
"""Run Stage 5C.2C estimator-failure autopsy for 3x3x3 replication only.

This stage is diagnostic. It holds the disorder seed block, shape, labels, model,
and fixed-time definition fixed, while changing trajectory seed offsets and/or
trajectory budgets to diagnose whether the Stage 5C.2B failure is true residual
trajectory noise, a small-between-disorder ratio effect, or a brittle gate.
"""
from __future__ import annotations
import argparse, json, shutil, subprocess, sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from haxs.io.result_store import ensure_dir, save_json

LOCKED_FILES = [
    'stage4_finals.csv',
    'stage4_curves_all.csv',
    'stage4_seed_averaged_finals.csv',
    'stage4_primary_pair_effects.csv',
    'stage4_nested_uncertainty.csv',
    'stage4_publication_campaign_manifest.json',
]

def run(cmd, transcript, marker=None, dry=False):
    line = ' '.join(map(str, cmd))
    if dry:
        print('DRY RUN:', line, flush=True); transcript.append('DRY RUN: ' + line); return
    print('RUN:', line, flush=True); transcript.append('RUN: ' + line)
    if marker is not None and marker.exists():
        print('SKIP existing:', marker, flush=True); transcript.append('SKIP existing: ' + str(marker)); return
    subprocess.run([str(x) for x in cmd], cwd=ROOT, check=True)

def make_candidate_cfg(raw, st, cand):
    return {
        'seed': raw.get('seed', 131001),
        'lattice': raw.get('lattice', {}),
        'model': raw.get('model', {}),
        'dtwa': dict(raw.get('dtwa', {}), n_traj=int(cand['n_traj'])),
        'stage4': {
            'bootstrap_samples': int(raw['stage4'].get('bootstrap_samples', 1000)),
            'ci': float(raw['stage4'].get('ci', 0.95)),
            'fixed_time_fraction': float(raw['stage4'].get('fixed_time_fraction', 0.65)),
            'trajectory_seed_stride': int(raw['stage4'].get('trajectory_seed_stride', 100000)),
            'trajectory_seed_offset': int(cand.get('trajectory_seed_offset', 0)),
            'seed_start': int(st['replication_seed_start']),
            'seeds': int(st['seeds_per_block']),
            'trajectory_reps': int(cand['trajectory_reps']),
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

def copy_locked_primary(src: Path, dest: Path):
    dest.mkdir(parents=True, exist_ok=True)
    copied = []
    for name in LOCKED_FILES:
        sp = src / name
        if sp.exists():
            dp = dest / name
            shutil.copy2(sp, dp)
            copied.append(name)
    return copied

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', default='configs/stage5c2c_lite/estimator_autopsy_3x3x3.yaml')
    ap.add_argument('--locked-primary', required=True, help='Path to locked 3x3x3 primary_campaign from Stage 5C.2')
    ap.add_argument('--out', default='results/stage5c2c_lite')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--no-copy-locked-primary', action='store_true')
    args = ap.parse_args()

    raw = yaml.safe_load((ROOT / args.config).read_text())
    st = raw['stage5c2c']
    locked = Path(args.locked_primary)
    locked = locked if locked.is_absolute() else ROOT / locked
    locked = locked.resolve()
    if not locked.exists():
        raise FileNotFoundError(f'Missing locked 3x3x3 primary campaign: {locked}')

    base = ensure_dir(ROOT / args.out)
    gen = ensure_dir(base / '_generated_configs')
    cand_root = ensure_dir(base / 'candidates')
    locked_dest = base / 'locked_primary_3x3x3'
    copied = [] if args.no_copy_locked_primary else copy_locked_primary(locked, locked_dest)
    transcript = []

    save_json(base / 'locked_primary_reference.json', {
        'stage': 'locked_3x3x3_primary_reference',
        'source_path_as_used': str(locked),
        'copied_into_package_relative_path': str(locked_dest.relative_to(ROOT)) if copied else None,
        'copied_files': copied,
        'note': 'For release, either include copied locked-primary tables or provide a verified dependency ZIP hash.',
    })

    for cand in st['candidate_grid']:
        tag = str(cand['tag'])
        cfg = make_candidate_cfg(raw, st, cand)
        cfg_path = gen / f'{tag}.yaml'
        cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False))
        out = cand_root / tag / 'replication_campaign'
        cmd = [sys.executable, 'scripts/run_stage4_publication_campaign.py', '--config', str(cfg_path.relative_to(ROOT)), '--out', str(out.relative_to(ROOT))]
        run(cmd, transcript, out / 'stage4_publication_campaign_manifest.json', dry=args.dry_run)

    (base / 'COMMAND_TRANSCRIPT_STAGE5C2C.txt').write_text('\n'.join(transcript) + '\n')
    save_json(base / 'stage5c2c_run_manifest.json', {
        'stage': 'stage5c2c_estimator_failure_autopsy',
        'locked_primary': str(locked),
        'candidate_grid': st['candidate_grid'],
        'dry_run': bool(args.dry_run),
        'claim_scope': st.get('claim_scope', ''),
    })
    print('Stage 5C.2C dry run complete.' if args.dry_run else 'Stage 5C.2C estimator autopsy candidate campaigns complete.')

if __name__ == '__main__':
    main()
