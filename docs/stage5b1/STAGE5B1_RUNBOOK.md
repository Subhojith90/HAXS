# Stage 5B1 Runbook

Purpose: replicated five-label mechanism decomposition for the selected 3x3x2 target after the Stage 5B0-R trajectory-fraction gate.

Run:

```bash
python -m pip install -e .
python scripts/run_tests.py
pytest tests/stage2 tests/stage3 tests/stage3a tests/stage4 tests/stage4a tests/stage4b tests/stage4c tests/stage4d tests/stage4e tests/stage4f tests/stage4g tests/stage5a tests/stage5aR tests/stage5a2 tests/stage5a3 tests/stage5b0 tests/stage5b0R tests/stage5b1 tests/regression -q
python scripts/run_stage5b1_all_lite.py
zip -r haxs_stage5b1_lite_results.zip results/stage5b1_lite figures/stage5b1_lite manuscript/stage5b1_lite reproducibility/stage5b1_source_manifest.json reproducibility/stage5b1_result_manifest.json docs/stage5b1
```

Claims allowed: replicated target-shape five-label preflight only. No finite-size, broad mechanism, or publication claim.
