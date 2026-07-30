from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[2]

def test_stage4g_scripts_exist():
    for name in [
        'run_stage4g_disorder_seed_expansion.py',
        'run_stage4g_all_lite.py',
        'make_stage4g_decision.py',
        'make_stage4g_report.py',
    ]:
        assert (ROOT/'scripts'/name).exists()

def test_stage4g_config_is_targeted_and_stronger_than_stage4e_lite():
    cfg=yaml.safe_load((ROOT/'configs/stage4g_lite/disorder_seed_expansion.yaml').read_text())
    assert cfg['stage4g']['target_shape']=='3x3x2'
    assert cfg['stage4g']['seeds'] >= 6
    assert cfg['stage4g']['trajectory_reps'] >= 4
    assert max(cfg['stage4g']['ntraj_sweep']) >= 16
    assert cfg['stage4g']['pass_requires']['negative_seed_fraction_at_least'] >= 0.67

def test_stage4g_full_recommended_config_exists():
    cfg=yaml.safe_load((ROOT/'configs/stage4g_lite/disorder_seed_expansion_full_recommended.yaml').read_text())
    assert cfg['stage4g']['seeds'] >= 16
    assert max(cfg['stage4g']['ntraj_sweep']) >= 64
