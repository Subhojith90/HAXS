from __future__ import annotations
import json
from pathlib import Path

def decision_markdown(decision_json: str | Path) -> str:
    d = json.loads(Path(decision_json).read_text())
    lines = [f"Decision: {d.get('status')}", f"Reason: {d.get('reason')}", "Route scores:"]
    for k, v in d.get("route_scores", {}).items():
        lines.append(f"- {k}: {v:.3f}")
    return "\n".join(lines)
