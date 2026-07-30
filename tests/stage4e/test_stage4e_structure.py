from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[2]

def test_stage4e_assets_exist():
    for p in [
        'configs/stage4e_lite/trajectory_stabilization.yaml',
        'scripts/run_stage4e_trajectory_stabilization.py',
        'scripts/run_stage4e_all_lite.py',
        'scripts/make_stage4e_decision.py',
        'scripts/make_stage4e_report.py',
        'scripts/make_stage4e_figures.py',
        'scripts/make_stage4e_manifest.py',
    ]:
        assert (ROOT/p).exists(), p

def test_stage4e_focuses_single_promising_shape():
    cfg=yaml.safe_load((ROOT/'configs/stage4e_lite/trajectory_stabilization.yaml').read_text())
    assert cfg['stage4e']['target_shape']=='3x3x2'
    shapes=[]
    for fam in cfg['stage4']['matched_families']:
        shapes.extend(fam['shapes'])
    assert shapes == [[3,3,2]]
    assert cfg['stage4']['seeds'] >= 4
    assert cfg['stage4']['trajectory_reps'] >= 2
    assert max(cfg['stage4e']['ntraj_sweep']) >= 8

def test_stage4e_claim_scope_is_not_publication_final():
    txt=(ROOT/'docs/stage4e/STAGE4E_RUNBOOK.md').read_text().lower()
    assert 'forbidden' in txt
    assert 'publication-grade claim' in txt
