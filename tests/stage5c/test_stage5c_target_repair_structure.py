from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[2]
def test_stage5c_target_repair_files_exist():
 for rel in ['configs/stage5c_target_repair_lite/target_repair_3x3x2.yaml','scripts/run_stage5c_target_repair.py','scripts/make_stage5c_target_repair_decision.py','scripts/run_stage5c_target_repair_all.py']:
  assert (ROOT/rel).exists(), rel
def test_stage5c_target_repair_config_is_not_broad_compute():
 raw=yaml.safe_load((ROOT/'configs/stage5c_target_repair_lite/target_repair_3x3x2.yaml').read_text())['stage5c_target_repair']
 assert raw['target_shape']==[3,3,2]
 assert raw['trajectory_reps']==10
 assert raw['ntraj']==256
 assert 'full_controlled' in raw['labels']
 assert len(raw['labels'])==5
