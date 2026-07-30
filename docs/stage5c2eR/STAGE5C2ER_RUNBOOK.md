# Stage 5C.2E-R Runbook

Stage 5C.2E-R is a dominant-variance precision re-lock after the Stage 5C.2D audit.

It does **not** launch Stage 5C3 production or Stage 5D.

## Purpose

The Stage 5C.2D audit found that primary uncertainty is dominated by hole-path and occupancy levels, not phase batches. Stage 5C.2E-R therefore appends primary data to a balanced target of `(I, J, K) = (16, 6, 4)` while keeping the confirmation block locked.

## Required inputs

Copy the Stage 5C.2D primary and confirmation directories into:

```bash
results/stage5c2d_lite/primary
results/stage5c2d_lite/confirmation
```

Each directory must contain the Stage 5C.2D CSV files.

## Commands

```bash
python -m pip install -e .
python scripts/run_tests.py
PYTHONPATH=src pytest tests/stage5c2eR tests/stage5c2d tests/random_effects tests/regression -q
python scripts/make_stage5c2eR_manifest.py --root . --out MANIFEST.source.sha256
python scripts/verify_manifest.py --root . --manifest MANIFEST.source.sha256
python scripts/run_stage5c2eR_all.py --dry-run
python scripts/run_stage5c2eR_all.py
column -s, -t < results/stage5c2eR/analysis/stage5c2eR_random_effects_gate_table.csv
column -s, -t < results/stage5c2eR/analysis/stage5c2eR_local_window_table.csv
column -s, -t < results/stage5c2eR/analysis/stage5c2eR_seed_namespace_audit.csv
cat results/stage5c2eR/analysis/stage5c2eR_decision.json
python scripts/make_stage5c2eR_manifest.py --root . --out MANIFEST.sha256
python scripts/verify_manifest.py --root . --manifest MANIFEST.sha256
```

## Claim boundary

Allowed: Stage 5C.2E-R tests whether the repaired primary block clears precision under a path/occupancy-balanced extension.

Forbidden: Stage 5C3 production approval, Stage 5D compute, finite-size claims, publication readiness, exact mobile-hole dynamics, and component-mechanism claims.
