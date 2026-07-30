from pathlib import Path
import yaml
ROOT = Path(__file__).resolve().parents[2]

def test_stage5b1_config_is_replicated_five_label():
    cfg = yaml.safe_load((ROOT/'configs/stage5b1_lite/replicated_five_label_3x3x2.yaml').read_text())
    st = cfg['stage5b1']
    assert st['target_shape'] == '3x3x2'
    assert st['ntraj'] >= 192
    assert len(st['block_seed_starts']) >= 2
    assert 'mobile_only' in st['mechanism_labels']
    assert 'spin_density_only' in st['mechanism_labels']
    assert st['trajectory_fraction_below'] <= 0.5

def test_stage5b1_scripts_exist():
    for name in ['run_stage5b1_all_lite.py','run_stage5b1_replicated_five_label.py','make_stage5b1_figures.py','make_stage5b1_decision.py','make_stage5b1_report.py','make_stage5b1_manifest.py']:
        assert (ROOT/'scripts'/name).exists()

def test_stage5b1_runbook_exists():
    assert (ROOT/'docs/stage5b1/STAGE5B1_RUNBOOK.md').exists()
