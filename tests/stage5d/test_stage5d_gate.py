from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_stage5d_gate_is_scaffold_only():
    p = ROOT / 'scripts/stage5d_design_review_gate.py'
    assert p.exists()
    txt = p.read_text()
    assert 'never launches Stage 5D broad compute' in txt
    assert "'stage5d_broad_compute_allowed': False" in txt or 'stage5d_broad_compute_allowed' in txt
    assert 'stage5c2b_decision.json' in txt
