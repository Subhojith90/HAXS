#!/usr/bin/env python
from pathlib import Path
import subprocess, sys
ROOT=Path(__file__).resolve().parents[1]
def run(cmd):
    print('RUN:', ' '.join(map(str,cmd)), flush=True)
    subprocess.run([str(x) for x in cmd], cwd=ROOT, check=True)
def main():
    run([sys.executable,'scripts/run_stage4_validation_stack.py','--out','results/stage5a3_lite'])
    run([sys.executable,'scripts/run_stage5a3_final_replication_lock.py','--config','configs/stage5a3_lite/final_replication_lock_3x3x2.yaml','--out','results/stage5a3_lite/final_replication_lock'])
    run([sys.executable,'scripts/make_stage5a3_figures.py','--results','results/stage5a3_lite','--out','figures/stage5a3_lite'])
    run([sys.executable,'scripts/make_stage5a3_decision.py','--results','results/stage5a3_lite','--out','results/stage5a3_lite/decision'])
    run([sys.executable,'scripts/make_stage5a3_report.py','--results','results/stage5a3_lite','--figures','figures/stage5a3_lite','--out','manuscript/stage5a3_lite'])
    run([sys.executable,'scripts/make_stage5a3_manifest.py','--package-root','.','--out','reproducibility/stage5a3_manifest.json'])
    print('Stage 5A3 lite complete.')
if __name__=='__main__': main()
