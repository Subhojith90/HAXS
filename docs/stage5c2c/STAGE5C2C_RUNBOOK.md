# Stage 5C.2C Runbook — Estimator-Failure Autopsy and Reproducibility Repair

Stage 5C.2C is approved as a diagnostic stage only. It diagnoses why the 3x3x3 replication block remains above the strict trajectory-fraction cutoff after Stage 5C.2B, while the sign, seed-level interval, local-window checks, and block compatibility remain strong.

## Claim boundary

Allowed:
- 3x3x3 replication estimator-failure autopsy.
- Absolute nested standard error and trajectory-fraction scaling diagnostics.
- Same-disorder independent trajectory-seed-block comparisons.

Forbidden:
- Stage 5D broad compute.
- Publication-readiness claim.
- Broad finite-size scaling claim.
- Component-mechanism proof.
- Exact mobile-hole dynamics claim.
- Constructive recovery or no-go theorem.

## Required locked input

Supply the locked Stage 5C.2 `3x3x3_primary_campaign` directory. For a release package, either copy it into:

```bash
results/locked/stage5c2_3x3x3_primary_campaign
```

or pass the path explicitly with `--locked-primary`. The Stage 5C.2C runner copies the minimal locked-primary tables into its output unless `--no-copy-locked-primary` is used.

## Commands

```bash
python -m pip install -e .
python scripts/run_tests.py
PYTHONPATH=src pytest tests/stage5c2c tests/stage5c2b tests/stage5d tests/regression -q

python scripts/run_stage5c2c_all.py \
  --locked-primary results/locked/stage5c2_3x3x3_primary_campaign \
  --dry-run

python scripts/run_stage5c2c_all.py \
  --locked-primary results/locked/stage5c2_3x3x3_primary_campaign

column -s, -t < results/stage5c2c_lite/analysis/stage5c2c_candidate_autopsy_table.csv
column -s, -t < results/stage5c2c_lite/analysis/stage5c2c_variance_scaling_table.csv
column -s, -t < results/stage5c2c_lite/analysis/stage5c2c_local_window_table.csv
cat results/stage5c2c_lite/analysis/stage5c2c_decision.json

python scripts/make_stage5c2c_manifest.py --root . --out MANIFEST.sha256
```

## Pass/fail logic

The existing strict fraction gate remains the only automatic route to Stage 5C3 design review. If absolute nested SE is small but the fraction gate remains failed, the output route is supervisor review, not success. Stage 5D remains blocked throughout.
