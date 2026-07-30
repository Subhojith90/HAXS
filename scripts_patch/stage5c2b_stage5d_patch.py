#!/usr/bin/env python
"""Verify Stage 5C.2B + gated Stage 5D scaffold patch files."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    'configs/stage5c2b_lite/replication_resolution_3x3x3.yaml',
    'scripts/run_stage5c2b_3x3x3_replication_resolution.py',
    'scripts/analyze_stage5c2b_decision.py',
    'scripts/run_stage5c2b_all.py',
    'scripts/stage5d_design_review_gate.py',
    'scripts/make_stage5c2b_manifest.py',
    'docs/stage5c2b/STAGE5C2B_RUNBOOK.md',
    'tests/stage5c2b/test_stage5c2b_scripts.py',
    'tests/stage5d/test_stage5d_gate.py',
]

def main():
    missing = []
    for rel in REQUIRED:
        p = ROOT / rel
        if not p.exists():
            missing.append(rel)
        else:
            print(f'verified {rel}')
    if missing:
        raise SystemExit('Missing Stage 5C.2B/5D patch files: ' + ', '.join(missing))
    print('Stage 5C.2B + gated Stage 5D scaffold patch is present. Broad Stage 5D compute remains blocked.')

if __name__ == '__main__':
    main()
