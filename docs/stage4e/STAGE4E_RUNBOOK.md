# Stage 4E: 3x3x2 Trajectory Stabilization

Stage 4E focuses only on the strongest surviving shape from Stage 4D: `3x3x2`.
It is designed to answer whether the fixed-time mechanism signal survives increased trajectory statistics.

## Run

```bash
cd hole_aware_xxz_squeezing_engine_stage4e_3x3x2_trajectory_stabilization
python -m pip install -e .
python scripts/run_tests.py
pytest tests/stage2 tests/stage3 tests/stage3a tests/stage3b tests/stage3c tests/stage4 tests/stage4a tests/stage4b tests/stage4c tests/stage4d tests/stage4e tests/regression -q
python scripts/run_stage4e_all_lite.py
zip -r haxs_stage4e_lite_results.zip results/stage4e_lite figures/stage4e_lite manuscript/stage4e_lite reproducibility/stage4e_manifest.json
```

## Scientific scope

Allowed: validated surrogate mechanism-stability diagnostic for one promising 3D shape.
Forbidden: publication-grade claim, exact quantum mobile-hole claim, constructive recovery, no-go theorem.
