# Stage 5C.1B/C.2 High-Power Conditional Pipeline

This version escalates C.1 replication resolution to n_traj=768 and trajectory_reps=24 after the n_traj=512, reps=16 run narrowly missed the trajectory-fraction gate. C.2 remains conditional and does not launch unless C.1B passes.

# Stage 5C.1 / 5C.2 Conditional Pipeline

This package advances without discarding the audit gates.

- **5C.1** reruns only the variance-limited replication block at `n_traj=512`, `trajectory_reps=16`, using the already completed Stage 5C target-repair primary campaign as its locked reference.
- **5C.2** is implemented in the same pipeline, but its two holdout geometries (`2x2x3`, `3x3x3`) run only when 5C.1 passes the corrected replication-core and component gates, local-window gate, and block-compatibility gate.
- Neither stage authorizes broad finite-size scaling or publication claims.

## Commands

```bash
python scripts_patch/stage5c1_c2_conditional_patch.py
PYTHONPATH=src pytest tests/stage5c1_c2 tests/stage5c tests/stage5b1R tests/regression -q
python scripts/run_stage5c1_c2_conditional_all.py --dry-run
python scripts/run_stage5c1_c2_conditional_all.py
```

If C.1 fails, the pipeline exits normally after writing `stage5c1_decision.json`; C.2 is not launched.
