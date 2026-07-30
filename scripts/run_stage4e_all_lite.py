#!/usr/bin/env python
from __future__ import annotations
import subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def run(cmd):
    print('RUN:', ' '.join(cmd), flush=True); subprocess.run(cmd,cwd=ROOT,check=True)
def main():
    run([sys.executable,'scripts/run_stage4_validation_stack.py','--out','results/stage4e_lite'])
    run([sys.executable,'scripts/run_stage4e_trajectory_stabilization.py','--config','configs/stage4e_lite/trajectory_stabilization.yaml','--out','results/stage4e_lite/trajectory_stabilization'])
    run([sys.executable,'scripts/make_stage4e_figures.py','--results','results/stage4e_lite','--out','figures/stage4e_lite'])
    run([sys.executable,'scripts/make_stage4e_decision.py','--results','results/stage4e_lite','--out','results/stage4e_lite/decision'])
    run([sys.executable,'scripts/make_stage4e_report.py','--results','results/stage4e_lite','--figures','figures/stage4e_lite','--out','manuscript/stage4e_lite'])
    run([sys.executable,'scripts/make_stage4e_manifest.py','--results','results/stage4e_lite','--out','reproducibility/stage4e_manifest.json'])
    print('Stage 4E lite complete.')
if __name__=='__main__': main()
