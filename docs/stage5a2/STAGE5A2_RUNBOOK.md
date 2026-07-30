# Stage 5A2 Runbook: Estimator-Convergence Repair and Independent Replication Gate

## Objective
Stage 5A2 is the supervisor-requested repair gate after Stage 5A-R. It does not make publication claims. It tests whether the selected 3x3x2 fixed-time mechanism signal survives a genuine high-trajectory trajectory sweep and independent seed-block replication.

## Required corrections implemented
- Uses true high-trajectory sweep in the lite gate: `ntraj = 24, 64, 128`.
- Preserves both `parent_config_hash` and `campaign_config_hash` for every generated campaign row.
- Reads the convergence plotting threshold from the generated convergence table/config, not a hard-coded value.
- Writes a package-wide manifest excluding caches, bytecode, and embedded ZIP files.
- Writes top-level and internal command transcripts.
- Adds skip/resume behavior for completed internal campaign and diagnosis outputs.

## Run commands
```bash
python -m pip install -e .
python scripts/run_tests.py
pytest tests/stage2 tests/stage3 tests/stage3a tests/stage3b tests/stage3c tests/stage4 tests/stage4a tests/stage4b tests/stage4c tests/stage4d tests/stage4e tests/stage4f tests/stage4g tests/stage5a tests/stage5aR tests/stage5a2 tests/regression -q
python scripts/run_stage5a2_all_lite.py
zip -r haxs_stage5a2_lite_results.zip results/stage5a2_lite figures/stage5a2_lite manuscript/stage5a2_lite reproducibility/stage5a2_manifest.json docs/stage5a2
```

## Pass/fail logic
Proceed to Stage 5B only if:
1. validation gates pass;
2. primary final block is negative with conservative interval excluding zero;
3. replication final block is negative with negative seed fraction at least 0.70;
4. last-two trajectory-count delta is below the configured tolerance;
5. trajectory fraction is below threshold or explicitly propagated.

If these fail, Stage 5B/5C remain blocked.
