from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[2]

def test_stage4d_assets_exist():
    for p in [
        'configs/stage4d_lite/targeted_publication_pilot.yaml',
        'scripts/run_stage4d_targeted_publication_pilot.py',
        'scripts/run_stage4d_all_lite.py',
        'scripts/make_stage4d_decision.py',
        'scripts/make_stage4d_report.py',
    ]:
        assert (ROOT/p).exists(), p

def test_stage4d_config_is_targeted_but_not_toy():
    cfg=yaml.safe_load((ROOT/'configs/stage4d_lite/targeted_publication_pilot.yaml').read_text())
    assert cfg['stage4']['seeds'] >= 8
    assert cfg['stage4']['trajectory_reps'] >= 4
    assert cfg['dtwa']['n_traj'] >= 16
    shapes=[tuple(s) for fam in cfg['stage4']['matched_families'] for s in fam['shapes']]
    assert (3,3,2) in shapes
    assert (2,2,2) in shapes

def test_stage4d_no_pandas_shape_attribute_bug():
    text=(ROOT/'scripts/run_stage4a_stability_diagnosis.py').read_text()
    assert "nested.shape ==" not in text
    assert "r.shape" not in text
    assert "nested['shape']" in text
    assert "r['shape']" in text
