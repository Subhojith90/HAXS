# Stage 4C0 Runbook

Stage 4C0 repairs the Stage 4B decision bookkeeping bug and performs a trajectory-scaling preflight before any disorder-seed scaling.

## What this stage fixes

- Replaces pandas `.shape` attribute misuse with explicit `['shape']` column access.
- Adds regression tests that would catch `shape=(19,)` outputs.
- Fixes ED-DTWA spin-length RMSE reporting key.
- Makes decision consistency depend on the nested uncertainty CSV.
- Runs a trajectory-count sweep before adding more disorder seeds.

## Commands

```bash
python -m pip install -e .
python scripts/run_tests.py
pytest tests/stage2 tests/stage3 tests/stage3a tests/stage3b tests/stage3c tests/stage4 tests/stage4a tests/stage4b tests/stage4c tests/regression -q
python scripts/run_stage4c0_all_lite.py
zip -r haxs_stage4c0_lite_results.zip results/stage4c_lite figures/stage4c_lite manuscript/stage4c_lite reproducibility/stage4c0_manifest.json
```

## Forbidden claims

No publication-grade mechanism proof, no robust 3D squeezing recovery, no no-go theorem, and no exact quantum mobile-hole claim.
