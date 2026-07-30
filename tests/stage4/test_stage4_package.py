from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[2]
def test_stage4_assets_exist():
    for p in ['configs/stage4_lite/publication_campaign.yaml','configs/stage4_full/publication_campaign.yaml','scripts/run_stage4_publication_campaign.py','scripts/run_stage4_all_lite.py','scripts/make_stage4_decision.py','scripts/make_stage4_report.py']:
        assert (ROOT/p).exists(), p

def test_stage4_config_has_publication_gates():
    cfg=yaml.safe_load((ROOT/'configs/stage4_lite/publication_campaign.yaml').read_text())
    assert cfg['stage4']['trajectory_reps'] >= 2
    assert cfg['stage4']['gates']['min_fixed_ci_shapes'] >= 1
    assert len(cfg['stage4']['matched_families']) >= 2
