#!/usr/bin/env python
from __future__ import annotations
import subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PY=sys.executable

def run(cmd):
    print('RUN:', ' '.join(cmd), flush=True)
    subprocess.run(cmd,cwd=ROOT,check=True)

def main():
    cfg='configs/stage4a_lite/stability_diagnosis.yaml'
    base='results/stage4a_lite'
    run([PY,'scripts/run_stage4_validation_stack.py','--out',base])
    run([PY,'scripts/run_stage4_publication_campaign.py','--config',cfg,'--out',base+'/publication_campaign'])
    run([PY,'scripts/run_stage4a_stability_diagnosis.py','--config',cfg,'--campaign-dir',base+'/publication_campaign','--out',base+'/stability_diagnosis'])
    run([PY,'scripts/make_stage4a_figures.py','--results',base,'--out','figures/stage4a_lite'])
    run([PY,'scripts/make_stage4a_decision.py','--results',base,'--out',base+'/decision'])
    run([PY,'scripts/make_stage4a_report.py','--results',base,'--figures','figures/stage4a_lite','--out','manuscript/stage4a_lite'])
    run([PY,'scripts/make_stage4a_manifest.py','--results',base,'--out','reproducibility/stage4a_manifest.json'])
    print('Stage 4A lite complete.')
if __name__=='__main__': main()
