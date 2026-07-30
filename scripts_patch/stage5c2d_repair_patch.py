
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=[
 'configs/stage5c2d_lite/nested_core_3x3x3.yaml',
 'src/haxs/validation/random_effects.py',
 'scripts/run_stage5c2d_nested_core.py',
 'scripts/analyze_stage5c2d_random_effects.py',
 'scripts/run_stage5c2d_all.py',
 'scripts/make_stage5c2d_manifest.py',
 'tests/stage5c2d/test_random_stream_separation.py',
 'tests/random_effects/test_random_effects_estimator.py',
 'README.md',
]
missing=[x for x in required if not (ROOT/x).exists()]
if missing: raise SystemExit('missing Stage 5C.2D files: '+', '.join(missing))
text=(ROOT/'src/haxs/methods/dtwa.py').read_text()
for token in ['occupancy_seed', 'hole_path_seed', 'phase_batch_seed']:
    if token not in text: raise SystemExit(f'dtwa missing explicit {token}')
print('Stage 5C.2D random-stream separation and random-effects repair patch is present. Stage 5D remains blocked.')
