from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[2]

def test_stage4f_scripts_exist():
    for name in [
        'run_stage4f_high_trajectory_confirmatory.py',
        'run_stage4f_all_lite.py',
        'make_stage4f_decision.py',
        'make_stage4f_report.py',
    ]:
        assert (ROOT/'scripts'/name).exists()

def test_stage4f_config_is_targeted_and_stronger_than_stage4e_lite():
    cfg=yaml.safe_load((ROOT/'configs/stage4f_lite/high_trajectory_confirmatory.yaml').read_text())
    assert cfg['stage4f']['target_shape']=='3x3x2'
    assert cfg['stage4f']['seeds'] >= 6
    assert cfg['stage4f']['trajectory_reps'] >= 4
    assert max(cfg['stage4f']['ntraj_sweep']) >= 16
    assert cfg['stage4f']['pass_requires']['negative_seed_fraction_at_least'] >= 0.67

def test_stage4f_full_recommended_config_exists():
    cfg=yaml.safe_load((ROOT/'configs/stage4f_lite/high_trajectory_confirmatory_full_recommended.yaml').read_text())
    assert cfg['stage4f']['seeds'] >= 16
    assert max(cfg['stage4f']['ntraj_sweep']) >= 64
