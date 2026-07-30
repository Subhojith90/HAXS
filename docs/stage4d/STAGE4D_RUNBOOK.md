# Stage 4D Runbook

Stage 4D is a targeted publication-pilot checkpoint. It does not claim constructive recovery, a no-go theorem, or exact quantum mobile-hole dynamics.

## Commands

```bash
python -m pip install -e .
python scripts/run_tests.py
pytest tests/stage2 tests/stage3 tests/stage3a tests/stage3b tests/stage3c tests/stage4 tests/stage4a tests/stage4b tests/stage4c tests/stage4d tests/regression -q
python scripts/run_stage4d_all_lite.py
zip -r haxs_stage4d_lite_results.zip results/stage4d_lite figures/stage4d_lite manuscript/stage4d_lite reproducibility/stage4d_manifest.json
```
