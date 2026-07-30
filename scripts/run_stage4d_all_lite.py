#!/usr/bin/env python
from __future__ import annotations
import subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PY=sys.executable

def run(args):
    print('RUN:', ' '.join(args), flush=True)
    subprocess.run(args,cwd=ROOT,check=True)

def main():
    run([PY,'scripts/run_stage4_validation_stack.py','--out','results/stage4d_lite'])
    run([PY,'scripts/run_stage4d_targeted_publication_pilot.py','--config','configs/stage4d_lite/targeted_publication_pilot.yaml','--out','results/stage4d_lite'])
    run([PY,'scripts/make_stage4d_figures.py','--results','results/stage4d_lite','--out','figures/stage4d_lite'])
    run([PY,'scripts/make_stage4d_decision.py','--results','results/stage4d_lite','--out','results/stage4d_lite/decision'])
    run([PY,'scripts/make_stage4d_report.py','--results','results/stage4d_lite','--figures','figures/stage4d_lite','--out','manuscript/stage4d_lite'])
    run([PY,'scripts/make_stage4d_manifest.py','--results','results/stage4d_lite','--out','reproducibility/stage4d_manifest.json'])
    print('Stage 4D lite complete.')
if __name__=='__main__': main()
