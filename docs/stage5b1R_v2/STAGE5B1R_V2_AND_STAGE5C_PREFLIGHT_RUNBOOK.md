# HAXS Stage 5B1-R v2 and conditional Stage 5C preflight

This package repairs the broken Stage 5B1-R curve diagnostic and adds genuine per-contrast nested uncertainty.
It **does not** authorize broad Stage 5C compute.

## Run order

```bash
python scripts_patch/stage5b1R_v2_and_stage5c_preflight_patch.py
PYTHONPATH=src pytest tests/stage5b1R tests/stage5b1 tests/stage5b0R tests/regression -q
rm -rf results/stage5b1R_lite/repaired_existing_v2
python scripts/run_stage5b1R_repair_existing_all.py
column -s, -t < results/stage5b1R_lite/repaired_existing_v2/stage5b1R_curve_based_local_window.csv
column -s, -t < results/stage5b1R_lite/repaired_existing_v2/stage5b1R_per_contrast_nested_uncertainty.csv
python scripts/run_stage5c_preflight_gate.py
cat results/stage5c_preflight/stage5c_preflight_decision.json
```

## Interpretation

- `stage5c_holdout_preflight_eligible: false` means remain at Stage 5B1-R. Run the planned 3x3x2 target repair with increased trajectory statistics; do not launch Stage 5C.
- `stage5c_holdout_preflight_eligible: true` would permit a **supervised holdout-geometry preflight only**. Broad finite-size Stage 5C remains locked by design.

## Scientific safeguards

The local-window script reads the registered `fixed_time` in `stage4_finals.csv`, locates the nearest actual curve time, and evaluates paired seed-level effects. The nested script reports, per contrast and block, between-disorder variance, within-trajectory variance, nested standard error, trajectory-fraction proxy, and explicit failure reasons.
