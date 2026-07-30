from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[2]

def test_stage5b0_entrypoints_exist():
    for rel in [
        'scripts/run_stage5b0_all_lite.py',
        'scripts/run_stage5b0_trajectory_lock_mechanism_pilot.py',
        'scripts/make_stage5b0_decision.py',
        'scripts/make_stage5b0_figures.py',
        'scripts/make_stage5b0_report.py',
        'scripts/make_stage5b0_manifest.py',
    ]:
        assert (ROOT/rel).exists(), rel

def test_stage5b0_config_has_five_labels_and_lock():
    cfg=yaml.safe_load((ROOT/'configs/stage5b0_lite/trajectory_fraction_lock_and_five_label_3x3x2.yaml').read_text())
    st=cfg['stage5b0']
    assert st['target_shape']=='3x3x2'
    assert st['ntraj_lock']>=128
    assert st['trajectory_reps_lock']>=8
    assert set(st['mechanism_labels'])=={'static_only','mobile_only','spin_density_only','mobile_plus_spin_density','everything'}

def test_stage5b0_gate_threshold_explicit():
    cfg=yaml.safe_load((ROOT/'configs/stage5b0_lite/trajectory_fraction_lock_and_five_label_3x3x2.yaml').read_text())
    assert cfg['stage5b0']['trajectory_fraction_below'] <= 0.5
    assert cfg['stage5b0']['block_compatibility_abs_db_below'] <= 0.25
