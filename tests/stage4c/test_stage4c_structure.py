from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[2]

def test_stage4c_assets_exist():
    for rel in [
        'configs/stage4c_lite/trajectory_scaling.yaml',
        'scripts/run_stage4c_trajectory_scaling.py',
        'scripts/make_stage4c_decision.py',
        'scripts/make_stage4c_report.py',
        'scripts/make_stage4c_manifest.py',
        'scripts/run_stage4c0_all_lite.py',
        'docs/stage4c/STAGE4C0_RUNBOOK.md',
    ]:
        assert (ROOT/rel).exists(), rel

def test_stage4c_config_is_trajectory_preflight():
    cfg=yaml.safe_load((ROOT/'configs/stage4c_lite/trajectory_scaling.yaml').read_text())
    assert cfg['stage4']['seeds'] >= 4
    assert cfg['stage4']['trajectory_reps'] >= 6
    assert len(cfg['stage4c0']['n_traj_sweep']) >= 2
    assert cfg['stage4c0']['required_real_shapes'] == ['3x3','2x2x2','3x3x2']
