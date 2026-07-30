#!/usr/bin/env python
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[1]
files=[
 "configs/stage5c1_c2_lite/conditional_pipeline.yaml",
 "scripts/run_stage5c1_replication_resolution.py",
 "scripts/make_stage5c1_decision.py",
 "scripts/run_stage5c2_holdout_preflight.py",
 "scripts/analyze_stage5c2_holdouts.py",
 "scripts/run_stage5c1_c2_conditional_all.py",
 "docs/stage5c1_c2/STAGE5C1_C2_RUNBOOK.md",
]
for rel in files:
    path=ROOT/rel
    if not path.exists():
        raise FileNotFoundError(path)
    print("verified", rel)
cfg=yaml.safe_load((ROOT/files[0]).read_text())["stage5c1_c2"]
assert int(cfg["replication_ntraj"]) == 768
assert int(cfg["replication_trajectory_reps"]) == 24
assert cfg["holdout_shapes"] == [[2,2,3],[3,3,3]]
print("Stage 5C.1B/C.2 conditional pipeline is present: replication n_traj=768, reps=24; C.2 remains gated.")
