#!/usr/bin/env python
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=[
 'configs/stage5c_target_repair_lite/target_repair_3x3x2.yaml',
 'scripts/run_stage5c_target_repair.py',
 'scripts/make_stage5c_target_repair_decision.py',
 'scripts/run_stage5c_target_repair_all.py',
 'scripts/run_stage5b1R_per_contrast_uncertainty.py',
]
for rel in required:
 p=ROOT/rel
 if not p.exists(): raise SystemExit(f'Missing required Stage 5C target-repair file: {rel}')
 print('verified',rel)
print('Stage 5C target-repair patch is present. This stage is target-shape-only; broad finite-size compute remains gated.')
