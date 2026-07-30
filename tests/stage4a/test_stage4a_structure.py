from pathlib import Path
import yaml
ROOT = Path(__file__).resolve().parents[2]

def test_stage4a_scripts_exist():
    for name in [
        'run_stage4a_all_lite.py',
        'run_stage4a_stability_diagnosis.py',
        'make_stage4a_figures.py',
        'make_stage4a_decision.py',
        'make_stage4a_report.py',
        'make_stage4a_manifest.py',
    ]:
        assert (ROOT / 'scripts' / name).exists()

def test_stage4a_config_has_nested_design():
    cfg = yaml.safe_load((ROOT / 'configs/stage4a_lite/stability_diagnosis.yaml').read_text())
    assert cfg['stage4']['trajectory_reps'] >= 2
    assert cfg['stage4']['seeds'] >= 4
    assert len(cfg['stage4']['matched_families']) >= 2
    assert cfg['stage4a']['effect_floor_db'] > 0
