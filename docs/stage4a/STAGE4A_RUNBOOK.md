# Stage 4A: Mechanism Stability Diagnosis

Purpose: diagnose why Stage 4 failed the publication gate under fixed-time and nested-uncertainty inference.

Run:

```bash
python -m pip install -e .
python scripts/run_tests.py
pytest tests/stage2 tests/stage3 tests/stage3a tests/stage3b tests/stage3c tests/stage4 tests/stage4a tests/regression -q
python scripts/run_stage4a_all_lite.py
zip -r haxs_stage4a_lite_results.zip results/stage4a_lite figures/stage4a_lite manuscript/stage4a_lite reproducibility/stage4a_manifest.json
```

Scientific scope: diagnosis only. This is not a publication claim package.
