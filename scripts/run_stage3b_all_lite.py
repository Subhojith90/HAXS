#!/usr/bin/env python
from __future__ import annotations
import subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PY=sys.executable
commands=[
 [PY,'scripts/run_stage3a_dtwa_validation.py','--config','configs/stage3a_lite/validation_repair.yaml','--out','results/stage3b_lite/dtwa_validation'],
 [PY,'scripts/run_stage3b_paired_finite_size.py','--config','configs/stage3b_lite/paired_finite_size.yaml','--out','results/stage3b_lite/paired_finite_size'],
 [PY,'scripts/make_stage3b_figures.py','--results','results/stage3b_lite','--out','figures/stage3b_lite'],
 [PY,'scripts/make_stage3b_decision.py','--results','results/stage3b_lite','--out','results/stage3b_lite/decision'],
 [PY,'scripts/make_stage3b_report.py','--results','results/stage3b_lite','--figures','figures/stage3b_lite','--out','manuscript/stage3b_lite'],
]
for cmd in commands:
    print('RUN:', ' '.join(cmd), flush=True)
    subprocess.run(cmd,cwd=ROOT,check=True)
print('Stage 3B lite complete.')
