from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_stage5c2b_files_exist():
    expected = [
        'configs/stage5c2b_lite/replication_resolution_3x3x3.yaml',
        'scripts/run_stage5c2b_3x3x3_replication_resolution.py',
        'scripts/analyze_stage5c2b_decision.py',
        'scripts/run_stage5c2b_all.py',
        'scripts/make_stage5c2b_manifest.py',
    ]
    for rel in expected:
        assert (ROOT / rel).exists(), rel


def test_stage5c2b_config_locked_scope():
    cfg = yaml.safe_load((ROOT / 'configs/stage5c2b_lite/replication_resolution_3x3x3.yaml').read_text())
    st = cfg['stage5c2b']
    assert st['shape'] == [3, 3, 3]
    assert st['replication_seed_start'] == 161001
    assert st['candidate_ntraj'] == [512, 768]
    assert st['candidate_reps'] == [16, 24]
    assert st['trajectory_fraction_below'] == 0.50
    assert st['block_compatibility_abs_db_below'] == 0.25


def test_stage5c2b_dry_run_requires_locked_primary(tmp_path):
    text = (ROOT / 'scripts/run_stage5c2b_3x3x3_replication_resolution.py').read_text()
    assert '--locked-primary' in text
    assert '3x3x3 replication-only' in text or 'replication-only' in text
