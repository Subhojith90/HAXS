#!/usr/bin/env python
from __future__ import annotations
import subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PYEXE=sys.executable

def run(args):
    print('RUN:', ' '.join(args), flush=True)
    subprocess.run(args,cwd=ROOT,check=True)

def main():
    run([PYEXE,'scripts/run_stage4_validation_stack.py','--out','results/stage4c_lite'])
    run([PYEXE,'scripts/run_stage4_publication_campaign.py','--config','configs/stage4c_lite/trajectory_scaling.yaml','--out','results/stage4c_lite/publication_campaign'])
    run([PYEXE,'scripts/run_stage4a_stability_diagnosis.py','--config','configs/stage4c_lite/trajectory_scaling.yaml','--campaign-dir','results/stage4c_lite/publication_campaign','--out','results/stage4c_lite/stability_diagnosis'])
    run([PYEXE,'scripts/run_stage4c_trajectory_scaling.py','--config','configs/stage4c_lite/trajectory_scaling.yaml','--out','results/stage4c_lite/trajectory_scaling'])
    run([PYEXE,'scripts/make_stage4c_figures.py','--results','results/stage4c_lite','--out','figures/stage4c_lite'])
    run([PYEXE,'scripts/make_stage4c_decision.py','--results','results/stage4c_lite','--out','results/stage4c_lite/decision'])
    run([PYEXE,'scripts/make_stage4c_report.py','--results','results/stage4c_lite','--figures','figures/stage4c_lite','--out','manuscript/stage4c_lite'])
    run([PYEXE,'scripts/make_stage4c_manifest.py','--results','results/stage4c_lite','--out','reproducibility/stage4c0_manifest.json'])
    print('Stage 4C0 lite complete.')
if __name__=='__main__': main()
