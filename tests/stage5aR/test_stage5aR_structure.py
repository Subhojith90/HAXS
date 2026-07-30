from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[2]

def test_stage5aR_files_exist():
    assert (ROOT/'scripts/run_stage5aR_repaired_convergence_replication.py').exists()
    assert (ROOT/'scripts/run_stage5aR_all_lite.py').exists()
    assert (ROOT/'configs/stage5aR_lite/convergence_replication_3x3x2_repaired.yaml').exists()
    assert (ROOT/'configs/stage5aR_full/convergence_replication_3x3x2_repaired_full.yaml').exists()
    assert (ROOT/'docs/stage5aR/STAGE5AR_RUNBOOK.md').exists()

def test_stage5aR_lite_uses_higher_trajectory_than_failed_stage5a():
    cfg=yaml.safe_load((ROOT/'configs/stage5aR_lite/convergence_replication_3x3x2_repaired.yaml').read_text())
    assert cfg['stage5a']['target_shape']=='3x3x2'
    assert max(cfg['stage5a']['ntraj_sweep']) >= 16
    assert cfg['stage5a']['trajectory_reps'] >= 2
    assert cfg['stage5a']['replication_seed_start'] != cfg['stage5a']['primary_seed_start']
    assert cfg['stage5a']['fixed_time_primary'] is True

def test_stage5aR_full_has_boss_requested_128_gate():
    cfg=yaml.safe_load((ROOT/'configs/stage5aR_full/convergence_replication_3x3x2_repaired_full.yaml').read_text())
    assert 64 in cfg['stage5a']['ntraj_sweep']
    assert 128 in cfg['stage5a']['ntraj_sweep']
    assert cfg['stage5a']['seeds_per_block'] >= 16

def test_stage5aR_script_preserves_hashes_and_safe_claims():
    txt=(ROOT/'scripts/run_stage5aR_repaired_convergence_replication.py').read_text()
    assert 'parent_config_hash' in txt
    assert 'campaign_config_hash' in txt
    assert 'no publication claim' in txt
