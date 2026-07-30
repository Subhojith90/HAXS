from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def test_stage5aR_no_publication_claim_in_decision_script():
    txt=(ROOT/'scripts/make_stage5aR_decision.py').read_text()
    assert 'publication_claim_allowed' in txt
    assert 'False' in txt
    assert 'no manuscript claim' in txt.lower()

def test_stage5aR_runbook_names_full_high_trajectory_gate():
    txt=(ROOT/'docs/stage5aR/STAGE5AR_RUNBOOK.md').read_text()
    assert '64' in txt and '128' in txt
    assert 'independent seed' in txt.lower()
