from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[2]

def test_stage5a_files_exist():
    assert (ROOT/'scripts/run_stage5a_convergence_replication.py').exists()
    assert (ROOT/'scripts/run_stage5a_all_lite.py').exists()
    assert (ROOT/'configs/stage5a_lite/convergence_replication_3x3x2.yaml').exists()
    assert (ROOT/'docs/stage5a/STAGE5A_RUNBOOK.md').exists()

def test_stage5a_config_preregistered():
    cfg=yaml.safe_load((ROOT/'configs/stage5a_lite/convergence_replication_3x3x2.yaml').read_text())
    assert cfg['stage5a']['target_shape']=='3x3x2'
    assert len(cfg['stage5a']['ntraj_sweep']) >= 2
    assert cfg['stage5a']['replication_seed_start'] != cfg['stage5a']['primary_seed_start']
    assert cfg['stage5a']['fixed_time_primary'] is True

def test_stage5a_script_records_parent_and_campaign_hashes():
    txt=(ROOT/'scripts/run_stage5a_convergence_replication.py').read_text()
    assert 'parent_config_hash' in txt
    assert 'campaign_config_hash' in txt
    assert 'stage5a_passed' in txt
