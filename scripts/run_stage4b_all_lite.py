#!/usr/bin/env python
from __future__ import annotations
import subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PYEXE=sys.executable

def run(cmd):
    print('RUN:', ' '.join(cmd), flush=True)
    subprocess.run(cmd,cwd=ROOT,check=True)

def main():
    cfg='configs/stage4b_lite/targeted_checkpoint.yaml'
    base='results/stage4b_lite'
    run([PYEXE,'scripts/run_stage4_validation_stack.py','--out',base])
    run([PYEXE,'scripts/run_stage4_publication_campaign.py','--config',cfg,'--out',base+'/publication_campaign'])
    run([PYEXE,'scripts/run_stage4a_stability_diagnosis.py','--config',cfg,'--campaign-dir',base+'/publication_campaign','--out',base+'/stability_diagnosis'])
    run([PYEXE,'scripts/make_stage4a_figures.py','--results',base,'--out','figures/stage4b_lite'])
    run([PYEXE,'scripts/make_stage4b_decision.py','--results',base,'--out',base+'/decision'])
    run([PYEXE,'scripts/make_stage4b_report.py','--results',base,'--figures','figures/stage4b_lite','--out','manuscript/stage4b_lite'])
    run([PYEXE,'scripts/make_stage4b_manifest.py','--results',base,'--out','reproducibility/stage4b_manifest.json'])
    print('Stage 4B lite complete.')
if __name__=='__main__': main()
