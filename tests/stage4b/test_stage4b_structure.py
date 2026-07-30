from pathlib import Path
import yaml
ROOT = Path(__file__).resolve().parents[2]

def test_stage4b_scripts_exist():
    for name in ['run_stage4b_all_lite.py','make_stage4b_decision.py','make_stage4b_report.py','make_stage4b_manifest.py']:
        assert (ROOT / 'scripts' / name).exists()

def test_stage4b_config_includes_stage4a_seed_fix():
    cfg = yaml.safe_load((ROOT / 'configs/stage4b_lite/targeted_checkpoint.yaml').read_text())
    assert cfg['stage4']['seeds'] >= 4
    assert cfg['stage4']['trajectory_reps'] >= 2
    assert len(cfg['stage4']['matched_families']) >= 2
    assert cfg['stage4a']['effect_floor_db'] > 0
