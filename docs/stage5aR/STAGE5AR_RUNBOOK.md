# Stage 5A-R Runbook: Repaired High-Trajectory Convergence and Replication Gate

## Objective
Stage 5A-R repairs the failed Stage 5A estimator by increasing trajectory resolution and keeping the experiment restricted to the target shape `3x3x2`.

This stage is a convergence and replication gate only. It does not permit publication claims.

## Lite command
```bash
python -m pip install -e .
python scripts/run_tests.py
pytest tests/stage2 tests/stage3 tests/stage3a tests/stage3b tests/stage3c tests/stage4 tests/stage4a tests/stage4b tests/stage4c tests/stage4d tests/stage4e tests/stage4f tests/stage4g tests/stage5a tests/stage5aR tests/regression -q
python scripts/run_stage5aR_all_lite.py
```

## Package results
```bash
zip -r haxs_stage5aR_lite_results.zip results/stage5aR_lite figures/stage5aR_lite manuscript/stage5aR_lite reproducibility/stage5aR_manifest.json docs/stage5aR
```

## Full gate design
The full pre-registered design includes `ntraj = 24, 64, 128`, independent seed blocks, at least 16 disorder seeds per block, and at least 6 trajectory repetitions.

## Pass logic
Proceed to Stage 5B only if:

1. DTWA and ED-DTWA validation gates pass.
2. The final high-trajectory fixed-time effect is negative.
3. The final t confidence interval excludes zero in the primary block.
4. The independent seed block remains negative.
5. The trajectory fraction is below 0.5 or explicitly propagated.
6. The convergence delta between the last two trajectory counts is below the pre-registered tolerance.

## Forbidden claims
Do not claim publication-grade mechanism proof, exact quantum mobile-hole dynamics, robust 3D recovery, no-go theorem, or constructive recovery.
