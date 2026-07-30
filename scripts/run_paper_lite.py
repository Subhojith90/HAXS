#!/usr/bin/env python
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

import subprocess, sys
cmds=[
 [sys.executable,'scripts/run_mechanism_decomposition.py','--config','configs/paper_lite/mechanism_decomposition.yaml','--out','results/paper_lite/mechanism'],
 [sys.executable,'scripts/run_inverse_design.py','--config','configs/paper_lite/optimization_lite.yaml','--out','results/paper_lite/optimization'],
 [sys.executable,'scripts/run_threshold_map.py','--config','configs/paper_lite/threshold_map_lite.yaml','--out','results/paper_lite/threshold'],
]
for cmd in cmds:
    subprocess.run(cmd,cwd=ROOT,check=True)
