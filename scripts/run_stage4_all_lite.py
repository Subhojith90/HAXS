#!/usr/bin/env python
from __future__ import annotations
import subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def run(cmd): print('RUN:', ' '.join([sys.executable]+cmd), flush=True); subprocess.check_call([sys.executable]+cmd,cwd=ROOT)
def main():
    run(['scripts/run_stage4_validation_stack.py','--out','results/stage4_lite'])
    run(['scripts/run_stage4_publication_campaign.py','--config','configs/stage4_lite/publication_campaign.yaml','--out','results/stage4_lite/publication_campaign'])
    run(['scripts/make_stage4_figures.py','--results','results/stage4_lite','--out','figures/stage4_lite'])
    run(['scripts/make_stage4_decision.py','--results','results/stage4_lite','--out','results/stage4_lite/decision'])
    run(['scripts/make_stage4_report.py','--results','results/stage4_lite','--out','manuscript/stage4_lite'])
    run(['scripts/make_stage4_manifest.py','--results','results/stage4_lite','--out','reproducibility/stage4_manifest.json'])
    print('Stage 4 lite complete.')
if __name__=='__main__': main()
