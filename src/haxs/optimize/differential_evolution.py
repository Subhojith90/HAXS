from __future__ import annotations
import numpy as np

def differential_evolution_available() -> bool:
    try:
        from scipy.optimize import differential_evolution  # noqa: F401
        return True
    except Exception:
        return False

def run_differential_evolution_stub(config: dict) -> dict[str, object]:
    if not differential_evolution_available():
        return {"available": False, "message": "SciPy differential_evolution unavailable; random_search used."}
    return {"available": True, "message": "Available but not used in laptop default to preserve deterministic runtime."}
