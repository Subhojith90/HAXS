#!/usr/bin/env python
from __future__ import annotations
import argparse, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def run(cmd):
    print('RUN:', ' '.join(map(str,cmd)), flush=True)
    subprocess.run([str(x) for x in cmd], cwd=ROOT, check=True)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--existing-primary', default='results/stage5c2d_lite/primary')
    ap.add_argument('--locked-confirmation', default='results/stage5c2d_lite/confirmation')
    ap.add_argument('--out', default='results/stage5c2eR')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--skip-fixed-count', action='store_true')
    a=ap.parse_args()
    if a.dry_run:
        run([sys.executable,'scripts/run_stage5c2eR_primary_extension.py','--existing-primary',a.existing_primary,'--out',f'{a.out}/primary','--dry-run'])
        if not a.skip_fixed_count:
            run([sys.executable,'scripts/run_stage5c2eR_fixed_count_pilot.py','--out',f'{a.out}/fixed_count_diagnostic','--dry-run'])
        print('Stage 5C.2E-R dry run complete.')
        return
    run([sys.executable,'scripts/run_stage4_validation_stack.py','--out',f'{a.out}/validation'])
    run([sys.executable,'scripts/run_stage5c2eR_primary_extension.py','--existing-primary',a.existing_primary,'--out',f'{a.out}/primary'])
    run([sys.executable,'scripts/analyze_stage5c2eR.py','--primary',f'{a.out}/primary','--locked-confirmation',a.locked_confirmation,'--out',f'{a.out}/analysis'])
    if not a.skip_fixed_count:
        run([sys.executable,'scripts/run_stage5c2eR_fixed_count_pilot.py','--out',f'{a.out}/fixed_count_diagnostic'])
    print('Stage 5C.2E-R all complete.')
if __name__=='__main__': main()
