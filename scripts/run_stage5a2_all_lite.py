#!/usr/bin/env python
from __future__ import annotations
import subprocess, sys, datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TRANSCRIPT=[]
def run(cmd):
    line=' '.join(cmd); print('RUN:', line, flush=True); TRANSCRIPT.append('RUN: '+line)
    subprocess.run(cmd,cwd=ROOT,check=True)
def main():
    py=sys.executable
    run([py,'scripts/run_stage4_validation_stack.py','--out','results/stage5a2_lite'])
    run([py,'scripts/run_stage5a2_estimator_convergence_replication.py','--config','configs/stage5a2_lite/estimator_convergence_replication_3x3x2.yaml','--out','results/stage5a2_lite/convergence_replication'])
    run([py,'scripts/make_stage5a2_figures.py','--results','results/stage5a2_lite','--out','figures/stage5a2_lite'])
    run([py,'scripts/make_stage5a2_decision.py','--results','results/stage5a2_lite','--out','results/stage5a2_lite/decision'])
    run([py,'scripts/make_stage5a2_report.py','--results','results/stage5a2_lite','--figures','figures/stage5a2_lite','--out','manuscript/stage5a2_lite'])
    run([py,'scripts/make_stage5a2_manifest.py','--package-root','.','--out','reproducibility/stage5a2_manifest.json'])
    out=ROOT/'results/stage5a2_lite/convergence_replication/TOP_LEVEL_COMMAND_TRANSCRIPT_STAGE5A2.txt'
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text('Stage 5A2 top-level transcript created '+datetime.datetime.now(datetime.UTC).isoformat()+'\n'+'\n'.join(TRANSCRIPT)+'\n')
    print('Stage 5A2 lite complete.')
if __name__=='__main__': main()
