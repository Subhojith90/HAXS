
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def test_curve_repair_script_exists():
    assert (ROOT / "scripts/run_stage5b1R_repair_existing_curves.py").exists()

def test_per_contrast_uncertainty_script_exists():
    assert (ROOT / "scripts/run_stage5b1R_per_contrast_uncertainty.py").exists()

def test_repair_wrapper_exists():
    assert (ROOT / "scripts/run_stage5b1R_repair_existing_all.py").exists()
