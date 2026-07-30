#!/usr/bin/env python
from __future__ import annotations
import subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def run(cmd):
    print('RUN:', ' '.join(cmd), flush=True)
    subprocess.run(cmd,cwd=ROOT,check=True)
def main():
    py=sys.executable
    run([py,'scripts/run_stage4_validation_stack.py','--out','results/stage5aR_lite'])
    run([py,'scripts/run_stage5aR_repaired_convergence_replication.py','--config','configs/stage5aR_lite/convergence_replication_3x3x2_repaired.yaml','--out','results/stage5aR_lite/convergence_replication'])
    run([py,'scripts/make_stage5aR_figures.py','--results','results/stage5aR_lite','--out','figures/stage5aR_lite'])
    run([py,'scripts/make_stage5aR_decision.py','--results','results/stage5aR_lite','--out','results/stage5aR_lite/decision'])
    run([py,'scripts/make_stage5aR_report.py','--results','results/stage5aR_lite','--figures','figures/stage5aR_lite','--out','manuscript/stage5aR_lite'])
    run([py,'scripts/make_stage5aR_manifest.py','--results','results/stage5aR_lite','--out','reproducibility/stage5aR_manifest.json'])
    print('Stage 5A-R lite complete.')
if __name__=='__main__': main()
