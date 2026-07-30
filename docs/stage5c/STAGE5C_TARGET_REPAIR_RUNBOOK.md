# Stage 5C Target-Repair Runbook

## Purpose
Run the next project stage without prematurely launching a broad finite-size campaign. This stage reruns only the registered 3x3x2 target with n_traj=256 and 10 trajectory repetitions in each independent seed block. It includes the curve-based local-window repair and corrected per-contrast nested variance decomposition.

## Included estimator correction
The trajectory fraction is computed as `(within_variance / reps) / (between_variance + within_variance / reps)`. This matches the nesting used for the standard error and avoids treating all within-seed variation as if it were a single-repetition estimate.

## Scope boundary
This is an advancement stage, not broad Stage 5C finite-size scaling. Passing it permits only a holdout-geometry preflight. It does not permit publication claims.

## Commands
```bash
python scripts_patch/stage5c_target_repair_patch.py
PYTHONPATH=src pytest tests/stage5c tests/stage5b1R tests/stage5b1 tests/stage5b0R tests/regression -q
python scripts/run_stage5c_target_repair_all.py
cat results/stage5c_target_repair_lite/decision/stage5c_target_repair_decision.json
```
