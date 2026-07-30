#!/usr/bin/env python
from __future__ import annotations
import argparse, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def run(cmd):
    print('RUN:', ' '.join(map(str, cmd)), flush=True)
    subprocess.run([str(x) for x in cmd], cwd=ROOT, check=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--locked-primary', required=True)
    ap.add_argument('--out', default='results/stage5c2c_lite')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    run([sys.executable, 'scripts/run_stage4_validation_stack.py', '--out', f'{args.out}/validation'])
    cmd = [sys.executable, 'scripts/run_stage5c2c_estimator_autopsy.py', '--locked-primary', args.locked_primary, '--out', args.out]
    if args.dry_run: cmd.append('--dry-run')
    run(cmd)
    if not args.dry_run:
        run([sys.executable, 'scripts/analyze_stage5c2c_estimator_autopsy.py', '--results', args.out])
    print('Stage 5C.2C dry-run all complete.' if args.dry_run else 'Stage 5C.2C all complete.')
if __name__ == '__main__': main()
