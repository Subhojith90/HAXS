from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def test_stage5c_scripts_exist():
    assert (ROOT / "scripts/run_stage5c_controlled_release.py").exists()
    assert (ROOT / "scripts/make_stage5c_controlled_report.py").exists()
    assert (ROOT / "scripts/run_stage5c_all_lite.py").exists()

def test_stage5c_config_exists():
    assert (ROOT / "configs/stage5c_lite/controlled_release.yaml").exists()
