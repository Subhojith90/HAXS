#!/usr/bin/env python
from __future__ import annotations
import subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def run(cmd):
 print('RUN:', ' '.join(map(str,cmd)),flush=True); subprocess.run([str(x) for x in cmd],cwd=ROOT,check=True)
def main():
 run([sys.executable,'scripts/run_stage4_validation_stack.py','--out','results/stage5c_target_repair_lite/validation'])
 run([sys.executable,'scripts/run_stage5c_target_repair.py'])
 run([sys.executable,'scripts/make_stage5c_target_repair_decision.py'])
 print('Stage 5C target-repair all complete.')
if __name__=='__main__': main()
