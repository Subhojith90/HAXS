# Stage 5B0 / Stage 5A4 Runbook

Objective: repair Stage 5A3 pass/fail semantics, close the trajectory-fraction gate for the locked 3x3x2 target, and run a five-label mechanism pilot only after the variance gate passes.

## Lite command

```bash
python -m pip install -e .
python scripts/run_tests.py
pytest tests/stage5b0 tests/stage5a3 tests/regression -q
python scripts/run_stage5b0_all_lite.py
```

## Package

```bash
zip -r haxs_stage5b0_lite_results.zip results/stage5b0_lite figures/stage5b0_lite manuscript/stage5b0_lite reproducibility/stage5b0_manifest.json docs/stage5b0
```

## Allowed claims

- Tested DTWA and ED-DTWA validation gates pass.
- The locked target-shape trajectory-fraction gate either passes or fails as reported.
- A five-label mechanism pilot is only a preflight, not a publication proof.

## Forbidden claims

- Publication-ready mechanism proof.
- General finite-size mechanism claim.
- Exact quantum mobile-hole dynamics.
- Constructive recovery or no-go theorem.
