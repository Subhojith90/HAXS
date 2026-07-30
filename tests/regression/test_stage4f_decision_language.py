from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def test_stage4f_decision_never_allows_publication_claim_directly():
    text=(ROOT/'scripts/make_stage4f_decision.py').read_text()
    assert "'publication_claim_allowed':False" in text.replace(' ', '')
    assert 'Supervisor review before Stage 5' in text
