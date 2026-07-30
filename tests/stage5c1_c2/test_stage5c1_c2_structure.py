from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[2]
def test_pipeline_files_exist():
 for rel in ['configs/stage5c1_c2_lite/conditional_pipeline.yaml','scripts/run_stage5c1_replication_resolution.py','scripts/make_stage5c1_decision.py','scripts/run_stage5c2_holdout_preflight.py','scripts/analyze_stage5c2_holdouts.py','scripts/run_stage5c1_c2_conditional_all.py']:
  assert (ROOT/rel).exists(), rel
def test_pipeline_is_gated():
 c=yaml.safe_load((ROOT/'configs/stage5c1_c2_lite/conditional_pipeline.yaml').read_text())['stage5c1_c2']
 assert c['replication_ntraj']==768
 assert c['replication_trajectory_reps']==24
 assert c['holdout_shapes']==[[2,2,3],[3,3,3]]
