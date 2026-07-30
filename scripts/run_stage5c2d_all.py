
#!/usr/bin/env python
from __future__ import annotations
import argparse, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def run(cmd):
    print('RUN:', ' '.join(map(str,cmd)), flush=True)
    subprocess.run([str(x) for x in cmd], cwd=ROOT, check=True)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--config',default='configs/stage5c2d_lite/nested_core_3x3x3.yaml'); ap.add_argument('--out',default='results/stage5c2d_lite'); ap.add_argument('--dry-run',action='store_true')
    a=ap.parse_args()
    if not a.dry_run:
        run([sys.executable,'scripts/run_stage4_validation_stack.py','--out',f'{a.out}/validation'])
    for block in ['primary','confirmation']:
        cmd=[sys.executable,'scripts/run_stage5c2d_nested_core.py','--config',a.config,'--block',block,'--out',f'{a.out}/{block}']
        if a.dry_run: cmd.append('--dry-run')
        run(cmd)
    if not a.dry_run:
        run([sys.executable,'scripts/analyze_stage5c2d_random_effects.py','--config',a.config,'--primary',f'{a.out}/primary','--confirmation',f'{a.out}/confirmation','--out',f'{a.out}/analysis'])
        print('Stage 5C.2D all complete.')
    else:
        print('Stage 5C.2D dry run complete.')
if __name__=='__main__': main()
