python -m pip install -e .
python scripts/run_tests.py
pytest tests/stage2 tests/stage3 tests/stage3a tests/stage3b tests/stage3c tests/stage4 tests/stage4a tests/stage4b tests/regression -q
python scripts/run_stage4b_all_lite.py
zip -r haxs_stage4b_lite_results.zip results/stage4b_lite figures/stage4b_lite manuscript/stage4b_lite reproducibility/stage4b_manifest.json
