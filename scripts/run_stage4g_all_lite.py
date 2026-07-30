#!/usr/bin/env python
from __future__ import annotations
import subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def run(cmd):
    print('RUN:', ' '.join(cmd), flush=True); subprocess.run(cmd,cwd=ROOT,check=True)
def main():
    run([sys.executable,'scripts/run_stage4_validation_stack.py','--out','results/stage4g_lite'])
    run([sys.executable,'scripts/run_stage4g_disorder_seed_expansion.py','--config','configs/stage4g_lite/disorder_seed_expansion.yaml','--out','results/stage4g_lite/disorder_seed_expansion'])
    run([sys.executable,'scripts/make_stage4g_figures.py','--results','results/stage4g_lite','--out','figures/stage4g_lite'])
    run([sys.executable,'scripts/make_stage4g_decision.py','--results','results/stage4g_lite','--out','results/stage4g_lite/decision'])
    run([sys.executable,'scripts/make_stage4g_report.py','--results','results/stage4g_lite','--figures','figures/stage4g_lite','--out','manuscript/stage4g_lite'])
    run([sys.executable,'scripts/make_stage4g_manifest.py','--results','results/stage4g_lite','--out','reproducibility/stage4g_manifest.json'])
    print('Stage 4G lite complete.')
if __name__=='__main__': main()
