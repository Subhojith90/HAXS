from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[2]

def test_stage3a_scripts_exist():
    for rel in [
        'scripts/run_stage3a_dtwa_validation.py',
        'scripts/run_stage3a_paired_mechanism.py',
        'scripts/make_stage3a_figures.py',
        'scripts/make_stage3a_decision.py',
        'scripts/make_stage3a_report.py',
        'scripts/run_stage3a_all_lite.py',
    ]:
        assert (ROOT/rel).exists(), rel

def test_stage3a_config_has_boss_gates():
    cfg=yaml.safe_load((ROOT/'configs/stage3a_lite/validation_repair.yaml').read_text())
    assert cfg['level']=='stage3a_lite'
    assert cfg['stage3a']['spin_length_min_after_first_step'] >= 0.90
    assert cfg['stage3a']['rerun_stage3_lite_after_repair'] is True

def test_stage3a_runbook_exists():
    assert (ROOT/'docs/stage3a/STAGE3A_RUNBOOK.md').exists()
    assert (ROOT/'STAGE3A_COMMANDS.sh').exists()
