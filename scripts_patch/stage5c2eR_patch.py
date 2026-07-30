from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=[
 'pyproject.toml',
 'configs/stage5c2eR/primary_I16_J6_K4.yaml',
 'configs/stage5c2eR/five_hole_diagnostic.yaml',
 'scripts/stage5c2eR_common.py',
 'scripts/run_stage5c2eR_primary_extension.py',
 'scripts/analyze_stage5c2eR.py',
 'scripts/run_stage5c2eR_fixed_count_pilot.py',
 'scripts/run_stage5c2eR_all.py',
 'scripts/make_stage5c2eR_manifest.py',
 'scripts/verify_manifest.py',
 'docs/stage5c2eR/STAGE5C2ER_RUNBOOK.md',
 'tests/stage5c2eR/test_stage5c2eR_structure.py',
]
missing=[]
for r in required:
    p=ROOT/r
    if not p.exists(): missing.append(r)
    else: print('verified', r)
if missing:
    raise SystemExit('Missing Stage 5C.2E-R files: '+', '.join(missing))
print('Stage 5C.2E-R dominant-variance precision re-lock patch is present. Stage 5C3 production and Stage 5D remain blocked.')
