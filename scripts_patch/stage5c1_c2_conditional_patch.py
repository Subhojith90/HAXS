#!/usr/bin/env python
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
files=['configs/stage5c1_c2_lite/conditional_pipeline.yaml','scripts/run_stage5c1_replication_resolution.py','scripts/make_stage5c1_decision.py','scripts/run_stage5c2_holdout_preflight.py','scripts/analyze_stage5c2_holdouts.py','scripts/run_stage5c1_c2_conditional_all.py','docs/stage5c1_c2/STAGE5C1_C2_RUNBOOK.md']
for rel in files:
 p=ROOT/rel
 if not p.exists(): raise FileNotFoundError(p)
 print('verified',rel)
print('Stage 5C.1/C.2 conditional pipeline is present. C.2 is implemented but cannot launch unless C.1 passes.')
