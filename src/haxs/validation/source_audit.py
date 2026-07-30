from __future__ import annotations
from pathlib import Path

def summarize_source_audit(proposal_dir: str | Path) -> dict[str, object]:
    p = Path(proposal_dir) / "reproducibility" / "source_status_audit.md"
    if not p.exists():
        return {"available": False, "verified_lines": 0, "text": ""}
    text = p.read_text(encoding="utf-8")
    return {"available": True, "verified_lines": text.lower().count("verified"), "text": text[:1200]}
