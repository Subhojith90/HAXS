# Stage 5A3 Runbook — Final 3x3x2 Replication Lock

Purpose: run the final target-shape replication lock after Stage 5A2 high-trajectory convergence evidence.

Scope:
- shape: `3x3x2` only
- fixed-time primary inference
- static_only minus mobile_plus_spin_density primary pair
- primary and independent replication seed blocks
- ntraj locked to 128
- larger seed block and trajectory repetition counts than the Stage 5A2 lite run

Run:

```bash
python -m pip install -e .
python scripts/run_tests.py
pytest tests/stage2 tests/stage3 tests/stage3a tests/stage3b tests/stage3c tests/stage4 tests/stage4a tests/stage4b tests/stage4c tests/stage4d tests/stage4e tests/stage4f tests/stage4g tests/stage5a tests/stage5aR tests/stage5a2 tests/stage5a3 tests/regression -q
python scripts/run_stage5a3_all_lite.py
```

Package:

```bash
zip -r haxs_stage5a3_lite_results.zip results/stage5a3_lite figures/stage5a3_lite manuscript/stage5a3_lite reproducibility/stage5a3_manifest.json docs/stage5a3
```

Allowed claim if passed: only that the 3x3x2 target-shape effect is locked under the specified surrogate estimator and seed-block design. No broad mechanism, finite-size, or publication claim is allowed until Stage 5B/5C.
