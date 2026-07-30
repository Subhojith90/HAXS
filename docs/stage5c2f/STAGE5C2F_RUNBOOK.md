# Stage 5C.2F Occupancy-Preserving Re-lock and Seed-Namespace Closure

## Locked design

Design A is preregistered: one completely fresh balanced 16 x 6 x 4 primary block. Each nominal occupancy index maps to one immutable occupancy seed, identifier, and physical hash. Paths and phase batches are nested beneath that identity. The frozen Stage 5C.2D confirmation is read-only.

No Stage 5C3 production, Stage 5D work, public release, or publication claim is authorized by this stage.

## S1: physical-cluster invariant gate

```bash
python scripts/check_stage5c2f_hierarchy.py --fail-on-collision --fail-on-multiple-occupancy-hash
```

## S2: fresh-unzip artifact gate

```bash
python scripts/run_stage5c2f_fresh_unzip_gate.py
```

Stop and submit immediately if either gate fails.

## M1: checkpointed primary re-lock

Run the complete locked workflow:

```bash
python scripts/run_stage5c2f_all.py
```

Or checkpoint by occupancy range, then resume the complete workflow:

```bash
python scripts/run_stage5c2f_primary_lock.py --occupancy-start 0 --occupancy-stop 4 --resume
python scripts/run_stage5c2f_all.py --resume
```

Every attempt is retained. Do not inspect or tune against partial scientific results.
