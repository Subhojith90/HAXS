
from pathlib import Path
import yaml
ROOT = Path(__file__).resolve().parents[2]

def test_stage5c2d_files_exist():
    for rel in [
        'configs/stage5c2d_lite/nested_core_3x3x3.yaml',
        'scripts/run_stage5c2d_nested_core.py',
        'scripts/analyze_stage5c2d_random_effects.py',
        'scripts/run_stage5c2d_all.py',
        'scripts/make_stage5c2d_manifest.py',
        'docs/stage5c2d/STAGE5C2D_RUNBOOK.md',
    ]:
        assert (ROOT/rel).exists(), rel

def test_stage5c2d_config_is_two_label_nested_design():
    cfg=yaml.safe_load((ROOT/'configs/stage5c2d_lite/nested_core_3x3x3.yaml').read_text())['stage5c2d']
    assert cfg['shape'] == [3,3,3]
    assert cfg['labels'] == ['static_only','mobile_plus_spin_density']
    assert cfg['occupancy_realizations'] >= 2
    assert cfg['paths_per_occupancy'] >= 2
    assert cfg['phase_batches_per_path'] >= 2
    assert cfg['blocks']['primary']['occupancy_seed_start'] != cfg['blocks']['confirmation']['occupancy_seed_start']
