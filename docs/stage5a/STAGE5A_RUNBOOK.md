# Stage 5A Runbook: Pre-Registered 3x3x2 Convergence and Replication Gate

## Purpose
Stage 5A decides whether the `3x3x2` fixed-time mechanism signal is sufficiently trajectory-converged and independently seed-replicated to justify Stage 5B mechanism decomposition.

## Lite run
```bash
python -m pip install -e .
python scripts/run_tests.py
pytest tests/stage2 tests/stage3 tests/stage3a tests/stage3b tests/stage3c tests/stage4 tests/stage4a tests/stage4b tests/stage4c tests/stage4d tests/stage4e tests/stage4f tests/stage4g tests/stage5a tests/regression -q
python scripts/run_stage5a_all_lite.py
zip -r haxs_stage5a_lite_results.zip results/stage5a_lite figures/stage5a_lite manuscript/stage5a_lite reproducibility/stage5a_manifest.json docs/stage5a
```

## Full intended run
Use `configs/stage5a_full/convergence_replication_3x3x2_full.yaml` and run `scripts/run_stage5a_convergence_replication.py` manually. The full design uses `ntraj = 64/128`, larger seed blocks, and stronger convergence tolerance.

## Gates
Proceed to Stage 5B only if:
- DTWA and ED-DTWA validation gates pass.
- Parent and campaign config hashes are recorded separately.
- High-trajectory fixed-time effect remains negative.
- High-trajectory t interval excludes zero.
- Independent seed block remains negative.
- Trajectory fraction is below the threshold or explicitly propagated.
- ntraj convergence delta is below the pre-registered tolerance.

## Claim policy
No publication claim is allowed from Stage 5A alone.
