#!/usr/bin/env python
from __future__ import annotations
import subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def run(cmd):
    print('RUN:', ' '.join(map(str,cmd)), flush=True)
    subprocess.run([str(x) for x in cmd], cwd=ROOT, check=True)
def main():
    run([sys.executable,'scripts/run_stage4_validation_stack.py','--out','results/stage5b1_lite'])
    run([sys.executable,'scripts/run_stage5b1_replicated_five_label.py','--config','configs/stage5b1_lite/replicated_five_label_3x3x2.yaml','--out','results/stage5b1_lite/replicated_five_label'])
    run([sys.executable,'scripts/make_stage5b1_figures.py','--results','results/stage5b1_lite','--out','figures/stage5b1_lite'])
    run([sys.executable,'scripts/make_stage5b1_decision.py','--results','results/stage5b1_lite','--out','results/stage5b1_lite/decision'])
    run([sys.executable,'scripts/make_stage5b1_report.py','--results','results/stage5b1_lite','--figures','figures/stage5b1_lite','--out','manuscript/stage5b1_lite'])
    run([sys.executable,'scripts/make_stage5b1_manifest.py','--package-root','.','--result-root','results/stage5b1_lite','--out-dir','reproducibility'])
    print('Stage 5B1 lite complete.')
if __name__=='__main__': main()
