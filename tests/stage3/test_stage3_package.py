from pathlib import Path
import yaml
ROOT = Path(__file__).resolve().parents[2]

def test_stage3_scripts_exist():
    for rel in [
        'scripts/run_stage3_seed_campaign.py',
        'scripts/run_stage3_finite_size.py',
        'scripts/run_stage3_mechanism_inference.py',
        'scripts/run_stage3_crossval_inference.py',
        'scripts/make_stage3_decision.py',
        'scripts/make_stage3_report.py',
        'scripts/run_stage3_all_lite.py',
    ]:
        assert (ROOT/rel).exists(), rel

def test_stage3_configs_have_publication_controls():
    for rel in ['configs/stage3_lite/publication_evidence.yaml','configs/stage3_full/publication_evidence.yaml']:
        cfg=yaml.safe_load((ROOT/rel).read_text())
        assert cfg['stage3']['seeds'] >= 50
        assert cfg['stage3']['bootstrap_samples'] >= 1000
        assert cfg['stage3']['folds'] >= 5
        assert len(cfg['stage3']['finite_size_shapes']) >= 5

def test_stage3_commands_exist():
    assert (ROOT/'STAGE3_COMMANDS.sh').exists()
    assert (ROOT/'docs/stage3/STAGE3_RUNBOOK.md').exists()
