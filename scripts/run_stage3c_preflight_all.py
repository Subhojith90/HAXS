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
    run([py,'scripts/run_stage3a_dtwa_validation.py','--config','configs/stage3a_lite/validation_repair.yaml','--out','results/stage3c_preflight/dtwa_validation'])
    run([py,'scripts/run_stage3c_ed_dtwa_gate.py','--config','configs/stage3c_preflight/preflight.yaml','--out','results/stage3c_preflight/ed_dtwa_gate'])
    run([py,'scripts/run_stage3c_fixed_time_nested.py','--config','configs/stage3c_preflight/preflight.yaml','--out','results/stage3c_preflight/fixed_time_nested'])
    run([py,'scripts/make_stage3c_preflight_figures.py','--results','results/stage3c_preflight','--out','figures/stage3c_preflight'])
    run([py,'scripts/make_stage3c_preflight_decision.py','--results','results/stage3c_preflight','--out','results/stage3c_preflight/decision'])
    run([py,'scripts/make_stage3c_preflight_report.py','--results','results/stage3c_preflight','--figures','figures/stage3c_preflight','--out','manuscript/stage3c_preflight'])
    run([py,'scripts/make_stage3c_manifest.py','--results','results/stage3c_preflight','--out','reproducibility/stage3c_preflight_manifest.json'])
    print('Stage 3C-preflight complete.')
if __name__=='__main__': main()
