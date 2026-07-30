"""Idempotent patch installer for Stage 5B1-R v2 and conditional Stage 5C preflight."""
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[1]
for rel in [
 'scripts/run_stage5b1R_repair_existing_curves.py',
 'scripts/run_stage5b1R_per_contrast_uncertainty.py',
 'scripts/run_stage5b1R_repair_existing_all.py',
 'scripts/run_stage5c_preflight_gate.py',
]:
 src=ROOT/rel; dst=ROOT/rel
 if not src.exists(): raise FileNotFoundError(src)
 print('verified',rel)
print('Stage 5B1-R v2 / Stage 5C conditional-preflight files are already present in this patched bundle.')
