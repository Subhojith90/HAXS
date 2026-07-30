#!/usr/bin/env python
"""One command: validation -> C.1 -> automatic C.1 gate -> conditional C.2 -> C.2 analysis."""
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def run(cmd): print('RUN:',' '.join(map(str,cmd)),flush=True); subprocess.run([str(x) for x in cmd],cwd=ROOT,check=True)
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',default='results/stage5c1_c2_lite');p.add_argument('--primary-reference',default='results/stage5c_target_repair_lite/primary_campaign');p.add_argument('--dry-run',action='store_true');a=p.parse_args()
 if a.dry_run:
  run([sys.executable,'scripts/run_stage5c1_replication_resolution.py','--out',a.out,'--primary-reference',a.primary_reference,'--dry-run']); return
 run([sys.executable,'scripts/run_stage4_validation_stack.py','--out',f'{a.out}/validation'])
 run([sys.executable,'scripts/run_stage5c1_replication_resolution.py','--out',a.out,'--primary-reference',a.primary_reference])
 run([sys.executable,'scripts/make_stage5c1_decision.py','--results',a.out])
 dec=json.loads((ROOT/a.out/'stage5c1_replication_resolution/decision/stage5c1_decision.json').read_text())
 if not dec['stage5c2_holdout_preflight_allowed']:
  print('C.1 did not pass. C.2 was intentionally not launched.'); return
 run([sys.executable,'scripts/run_stage5c2_holdout_preflight.py','--out',a.out])
 run([sys.executable,'scripts/analyze_stage5c2_holdouts.py','--results',a.out])
 print('Conditional Stage 5C.1/5C.2 pipeline complete.')
if __name__=='__main__':main()
