from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[2]

def test_stage5a3_files_exist():
    assert (ROOT/'scripts/run_stage5a3_final_replication_lock.py').exists()
    assert (ROOT/'scripts/run_stage5a3_all_lite.py').exists()
    assert (ROOT/'scripts/make_stage5a3_manifest.py').exists()
    assert (ROOT/'configs/stage5a3_lite/final_replication_lock_3x3x2.yaml').exists()
    assert (ROOT/'configs/stage5a3_full/final_replication_lock_3x3x2_full.yaml').exists()
    assert (ROOT/'docs/stage5a3/STAGE5A3_RUNBOOK.md').exists()

def test_stage5a3_lite_is_locked_high_trajectory_replication():
    cfg=yaml.safe_load((ROOT/'configs/stage5a3_lite/final_replication_lock_3x3x2.yaml').read_text())
    assert cfg['stage5a']['target_shape']=='3x3x2'
    assert cfg['stage5a']['ntraj_lock']==128
    assert cfg['stage5a']['ntraj_sweep']==[128]
    assert cfg['stage5a']['seeds_per_block']>=8
    assert cfg['stage5a']['trajectory_reps']>=4
    assert cfg['stage5a']['replication_seed_start'] != cfg['stage5a']['primary_seed_start']

def test_stage5a3_full_is_larger_than_lite():
    lite=yaml.safe_load((ROOT/'configs/stage5a3_lite/final_replication_lock_3x3x2.yaml').read_text())
    full=yaml.safe_load((ROOT/'configs/stage5a3_full/final_replication_lock_3x3x2_full.yaml').read_text())
    assert full['stage5a']['ntraj_lock']==128
    assert full['stage5a']['seeds_per_block']>=lite['stage5a']['seeds_per_block']
    assert full['stage5a']['trajectory_reps']>=lite['stage5a']['trajectory_reps']

def test_stage5a3_script_has_two_blocks_and_no_publication_claim():
    txt=(ROOT/'scripts/run_stage5a3_final_replication_lock.py').read_text()
    assert 'primary_seed_start' in txt
    assert 'replication_seed_start' in txt
    assert 'parent_config_hash' in txt
    assert 'campaign_config_hash' in txt
    assert 'no publication' in txt

