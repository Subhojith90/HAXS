#!/usr/bin/env python
from __future__ import annotations
import subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def run(args):
    print('RUN:', ' '.join(map(str,args)), flush=True)
    subprocess.run([str(x) for x in args], cwd=ROOT, check=True)
def main():
    run([sys.executable,'scripts/run_stage4_validation_stack.py','--out','results/stage5a_lite'])
    run([sys.executable,'scripts/run_stage5a_convergence_replication.py','--config','configs/stage5a_lite/convergence_replication_3x3x2.yaml','--out','results/stage5a_lite/convergence_replication'])
    run([sys.executable,'scripts/make_stage5a_figures.py','--results','results/stage5a_lite','--out','figures/stage5a_lite'])
    run([sys.executable,'scripts/make_stage5a_decision.py','--results','results/stage5a_lite','--out','results/stage5a_lite/decision'])
    run([sys.executable,'scripts/make_stage5a_report.py','--results','results/stage5a_lite','--figures','figures/stage5a_lite','--out','manuscript/stage5a_lite'])
    run([sys.executable,'scripts/make_stage5a_manifest.py','--results','results/stage5a_lite','--out','reproducibility/stage5a_manifest.json'])
    print('Stage 5A lite complete.')
if __name__=='__main__': main()
