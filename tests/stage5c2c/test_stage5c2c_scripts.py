from pathlib import Path
import yaml
ROOT = Path(__file__).resolve().parents[2]

def test_stage5c2c_files_exist():
    for rel in [
        'configs/stage5c2c_lite/estimator_autopsy_3x3x3.yaml',
        'scripts/run_stage5c2c_estimator_autopsy.py',
        'scripts/analyze_stage5c2c_estimator_autopsy.py',
        'scripts/run_stage5c2c_all.py',
        'scripts/make_stage5c2c_manifest.py',
        'docs/stage5c2c/STAGE5C2C_RUNBOOK.md',
    ]:
        assert (ROOT / rel).exists(), rel

def test_stage5c2c_config_gated():
    cfg = yaml.safe_load((ROOT / 'configs/stage5c2c_lite/estimator_autopsy_3x3x3.yaml').read_text())
    st = cfg['stage5c2c']
    assert st['shape'] == [3,3,3]
    assert st['replication_seed_start'] == 161001
    assert st['trajectory_fraction_below'] == 0.50
    assert st['absolute_nested_se_below'] > 0
    assert len(st['candidate_grid']) >= 2
    assert cfg['stage5d']['broad_compute_allowed'] is False

def test_stage4_supports_trajectory_seed_offset():
    txt = (ROOT / 'scripts/run_stage4_publication_campaign.py').read_text()
    assert 'trajectory_seed_offset' in txt
    assert 'seed_offset' in txt
