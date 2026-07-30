from pathlib import Path
import yaml
ROOT = Path(__file__).resolve().parents[2]

def test_stage5b0R_config_has_adaptive_candidates():
    cfg = yaml.safe_load((ROOT/'configs/stage5b0R_lite/adaptive_trajectory_lock_and_five_label_3x3x2.yaml').read_text())
    st = cfg['stage5b0R']
    assert st['target_shape'] == '3x3x2'
    assert len(st['adaptive_candidates']) >= 2
    assert max(c['ntraj'] for c in st['adaptive_candidates']) >= 192
    assert st['run_five_label_only_if_lock_passes'] is True
    assert 'mobile_only' in st['mechanism_labels']
    assert 'spin_density_only' in st['mechanism_labels']

def test_stage5b0R_scripts_exist():
    for name in [
        'run_stage5b0R_all_lite.py',
        'run_stage5b0R_adaptive_trajectory_lock.py',
        'make_stage5b0R_figures.py',
        'make_stage5b0R_decision.py',
        'make_stage5b0R_report.py',
        'make_stage5b0R_manifest.py',
    ]:
        assert (ROOT/'scripts'/name).exists()

def test_stage5b0R_runbook_exists():
    assert (ROOT/'docs/stage5b0R/STAGE5B0R_RUNBOOK.md').exists()
