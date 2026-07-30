#!/usr/bin/env python
from __future__ import annotations
import subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def run(cmd):
    print('RUN:', ' '.join(cmd), flush=True); subprocess.run(cmd,cwd=ROOT,check=True)
def main():
    run([sys.executable,'scripts/run_stage4_validation_stack.py','--out','results/stage4f_lite'])
    run([sys.executable,'scripts/run_stage4f_high_trajectory_confirmatory.py','--config','configs/stage4f_lite/high_trajectory_confirmatory.yaml','--out','results/stage4f_lite/high_trajectory_confirmatory'])
    run([sys.executable,'scripts/make_stage4f_figures.py','--results','results/stage4f_lite','--out','figures/stage4f_lite'])
    run([sys.executable,'scripts/make_stage4f_decision.py','--results','results/stage4f_lite','--out','results/stage4f_lite/decision'])
    run([sys.executable,'scripts/make_stage4f_report.py','--results','results/stage4f_lite','--figures','figures/stage4f_lite','--out','manuscript/stage4f_lite'])
    run([sys.executable,'scripts/make_stage4f_manifest.py','--results','results/stage4f_lite','--out','reproducibility/stage4f_manifest.json'])
    print('Stage 4F lite complete.')
if __name__=='__main__': main()
