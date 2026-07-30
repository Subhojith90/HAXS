# Stage 4 Publication-Mechanism Campaign Runbook

This stage is for validated surrogate mechanism evidence only.

```bash
python -m pip install -e .
python scripts/run_tests.py
pytest tests/stage2 tests/stage3 tests/stage3a tests/stage3b tests/stage3c tests/stage4 tests/regression -q
python scripts/run_stage4_all_lite.py
zip -r haxs_stage4_lite_results.zip results/stage4_lite figures/stage4_lite manuscript/stage4_lite reproducibility/stage4_manifest.json
```
