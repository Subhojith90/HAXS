#!/usr/bin/env python
from __future__ import annotations
import argparse, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def run(cmd):
    print('RUN:', ' '.join([sys.executable]+cmd), flush=True); subprocess.check_call([sys.executable]+cmd,cwd=ROOT)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--out',default='results/stage4_lite')
    args=ap.parse_args(); out=args.out
    run(['scripts/run_stage3a_dtwa_validation.py','--config','configs/stage3a_lite/validation_repair.yaml','--out',f'{out}/dtwa_validation'])
    run(['scripts/run_stage3c_ed_dtwa_gate.py','--config','configs/stage3c_preflight/preflight.yaml','--out',f'{out}/ed_dtwa_gate'])
if __name__=='__main__': main()
