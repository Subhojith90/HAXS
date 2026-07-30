# Stage 4F Runbook

Run the commands from the project root:

```bash
python -m pip install -e .
python scripts/run_tests.py
pytest tests/stage2 tests/stage3 tests/stage3a tests/stage3b tests/stage3c tests/stage4 tests/stage4a tests/stage4b tests/stage4c tests/stage4d tests/stage4e tests/stage4f tests/regression -q
python scripts/run_stage4f_all_lite.py
zip -r haxs_stage4f_lite_results.zip results/stage4f_lite figures/stage4f_lite manuscript/stage4f_lite reproducibility/stage4f_manifest.json
```

Full recommended config is available at:

`configs/stage4f_lite/high_trajectory_confirmatory_full_recommended.yaml`
