from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[2]

def test_stage3c_scripts_exist():
    for name in [
        'run_stage3c_ed_dtwa_gate.py',
        'run_stage3c_fixed_time_nested.py',
        'make_stage3c_preflight_figures.py',
        'make_stage3c_preflight_decision.py',
        'make_stage3c_preflight_report.py',
        'make_stage3c_manifest.py',
        'run_stage3c_preflight_all.py',
    ]:
        assert (ROOT/'scripts'/name).exists()

def test_stage3c_config_has_preflight_gates():
    cfg=yaml.safe_load((ROOT/'configs/stage3c_preflight/preflight.yaml').read_text())
    assert cfg['stage3c']['trajectory_reps'] >= 2
    assert cfg['stage3c']['pass_min_fixed_ci_shapes'] >= 2
    assert cfg['validation']['xi2_db_rmse_threshold'] <= 0.15
    assert cfg['provenance']['forbid_stale_spin_length_collapse'] is True

def test_stage3c_runbook_exists():
    text=(ROOT/'docs/stage3c/STAGE3C_PREFLIGHT_RUNBOOK.md').read_text()
    assert 'ED-DTWA' in text
    assert 'fixed-time' in text
    assert 'nested' in text
