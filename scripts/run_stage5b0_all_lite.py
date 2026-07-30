#!/usr/bin/env python
from __future__ import annotations
import subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def run(cmd):
    print('RUN:', ' '.join(map(str,cmd)), flush=True)
    subprocess.run([str(x) for x in cmd], cwd=ROOT, check=True)
def main():
    run([sys.executable,'scripts/run_stage4_validation_stack.py','--out','results/stage5b0_lite'])
    run([sys.executable,'scripts/run_stage5b0_trajectory_lock_mechanism_pilot.py','--config','configs/stage5b0_lite/trajectory_fraction_lock_and_five_label_3x3x2.yaml','--out','results/stage5b0_lite'])
    run([sys.executable,'scripts/make_stage5b0_figures.py','--results','results/stage5b0_lite','--out','figures/stage5b0_lite'])
    run([sys.executable,'scripts/make_stage5b0_decision.py','--results','results/stage5b0_lite','--out','results/stage5b0_lite/decision'])
    run([sys.executable,'scripts/make_stage5b0_report.py','--results','results/stage5b0_lite','--figures','figures/stage5b0_lite','--out','manuscript/stage5b0_lite'])
    run([sys.executable,'scripts/make_stage5b0_manifest.py','--package-root','.','--out','reproducibility/stage5b0_manifest.json'])
    print('Stage 5B0 lite complete.')
if __name__=='__main__': main()
