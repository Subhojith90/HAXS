#!/usr/bin/env python
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=[
 'configs/stage5c2c_lite/estimator_autopsy_3x3x3.yaml',
 'scripts/run_stage5c2c_estimator_autopsy.py',
 'scripts/analyze_stage5c2c_estimator_autopsy.py',
 'scripts/run_stage5c2c_all.py',
 'scripts/make_stage5c2c_manifest.py',
 'docs/stage5c2c/STAGE5C2C_RUNBOOK.md',
 'tests/stage5c2c/test_stage5c2c_scripts.py',
 'README.md',
]
for rel in required:
    p=ROOT/rel
    if not p.exists(): raise FileNotFoundError(rel)
    print('verified', rel)
print('Stage 5C.2C estimator-autopsy and reproducibility-repair patch is present. Stage 5D remains blocked.')
