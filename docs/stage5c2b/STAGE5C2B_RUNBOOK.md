# Stage 5C.2B Runbook: 3x3x3 Replication-Only Variance Resolution

## Purpose

Stage 5C.2B resolves the only remaining Stage 5C.2 holdout failure: the `3x3x3` replication block trajectory-fraction gate. It does **not** rerun the already-passed `2x2x3` blocks or the locked `3x3x3` primary block.

## Claim boundary

Allowed after a pass:

- `3x3x3` replication core fixed-time gate passed under the repaired estimator diagnostic.
- Target plus two holdout core diagnostics can proceed to Stage 5C3 design review.

Still forbidden:

- broad finite-size Stage 5C/5D compute;
- publication-ready claims;
- component-mechanism proof;
- exact mobile-hole dynamics;
- constructive recovery/no-go theorem.

## Required locked input

Provide the locked Stage 5C.2 `3x3x3_primary_campaign` folder from the previous checkpoint.

Example:

```bash
--locked-primary results/stage5c1_c2_lite/stage5c2_holdout_preflight/3x3x3_primary_campaign
```

## Fresh extraction check

```bash
python -m pip install -e .
PYTHONPATH=src pytest tests/stage5c2b tests/stage5d tests/stage5c1_c2 tests/stage5c tests/stage5b1R tests/regression -q
```

## Dry run

```bash
python scripts/run_stage5c2b_all.py \
  --locked-primary results/stage5c1_c2_lite/stage5c2_holdout_preflight/3x3x3_primary_campaign \
  --dry-run
```

## Real run

```bash
python scripts/run_stage5c2b_all.py \
  --locked-primary results/stage5c1_c2_lite/stage5c2_holdout_preflight/3x3x3_primary_campaign
```

## Inspect outputs

```bash
column -s, -t < results/stage5c2b_lite/analysis/stage5c2b_candidate_gate_table.csv
column -s, -t < results/stage5c2b_lite/analysis/stage5c2b_local_window_table.csv
cat results/stage5c2b_lite/analysis/stage5c2b_decision.json
cat results/stage5d_design_review/stage5d_gate_decision.json
```

## Pass criteria

The selected candidate passes only if:

- mean fixed-time core effect is negative;
- seed-level CI high endpoint is below zero;
- negative seed fraction is at least 0.70;
- trajectory fraction is below 0.50;
- all curve-derived local windows are negative;
- block delta against locked primary is below 0.25 dB.
