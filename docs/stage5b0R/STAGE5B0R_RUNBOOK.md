# Stage 5B0-R Runbook

## Objective
Adaptive trajectory-fraction lock for the 3x3x2 target shape, followed by a gated five-label mechanism pilot only if the variance lock passes.

## Run
```bash
python -m pip install -e .
python scripts/run_tests.py
pytest tests/stage2 tests/stage3 tests/stage3a tests/stage4 tests/stage4a tests/stage4b tests/stage4c tests/stage4d tests/stage4e tests/stage4f tests/stage4g tests/stage5a tests/stage5aR tests/stage5a2 tests/stage5a3 tests/stage5b0 tests/stage5b0R tests/regression -q
python scripts/run_stage5b0R_all_lite.py
zip -r haxs_stage5b0R_lite_results.zip results/stage5b0R_lite figures/stage5b0R_lite manuscript/stage5b0R_lite reproducibility/stage5b0R_manifest.json docs/stage5b0R
```

## Stop/go logic
Proceed to Stage 5B full only if the trajectory-fraction lock passes and the five-label pilot gives interpretable component-level evidence.

## Forbidden claims
No publication readiness, no broad finite-size claim, no exact quantum mobile-hole proof, and no constructive recovery claim.
