from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[2]

def test_stage3b_files_exist():
    required=[
        'configs/stage3b_lite/paired_finite_size.yaml',
        'scripts/run_stage3b_paired_finite_size.py',
        'scripts/run_stage3b_all_lite.py',
        'scripts/make_stage3b_decision.py',
        'scripts/make_stage3b_figures.py',
        'scripts/make_stage3b_report.py',
        'docs/stage3b/STAGE3B_RUNBOOK.md',
    ]
    for rel in required:
        assert (ROOT/rel).exists(), rel

def test_stage3b_config_has_multiple_shapes_and_core_pair():
    cfg=yaml.safe_load((ROOT/'configs/stage3b_lite/paired_finite_size.yaml').read_text())
    st=cfg['stage3b']
    assert len(st['shapes']) >= 5
    assert len(st['labels']) >= 5
    assert st['core_pair'] == ['static_only','mobile_plus_spin_density']
    assert st['seeds'] >= 12

def test_stage3b_forbids_constructive_claim_in_readme():
    txt=(ROOT/'docs/stage3b/STAGE3B_RUNBOOK.md').read_text().lower()
    assert 'forbidden' in txt
    assert '3 db constructive recovery' in txt
