# Stage 5C.2G Fixed-Hole/Topology Control and Small-System Validity Gate

This stage contains two independent gates. It does not authorize Stage 5C3 production, Stage 5D, manuscript-result claims, or public release.

## Phase 0: tests, invariant plan, and external protocol timestamp

Run the full tests and planned invariant gate before producing the candidate lock:

```bash
python scripts/run_tests.py
PYTHONPATH=src pytest tests/stage5c2g tests/stage5c2f tests/random_effects tests/regression -q
python scripts/run_stage5c2f_fresh_unzip_gate.py
python scripts/check_stage5c2g_invariants.py
python scripts/verify_stage5c2g_protocol_lock.py --config configs/stage5c2g/protocol.yaml
```

Publish the printed candidate SHA-256 through an externally timestamped channel. Save the resulting receipt as a text file that contains the exact SHA-256. Then finalize:

```bash
python scripts/verify_stage5c2g_protocol_lock.py \
  --config configs/stage5c2g/protocol.yaml \
  --external-receipt /absolute/path/to/external_timestamp_receipt.txt \
  --finalize
```

Do not modify covered code or configurations after finalization. Every runner checks the lock and will refuse to start if a covered hash changes.

## Experiment B calibration and tolerance lock

Calibration must occur before untouched validation:

```bash
python scripts/run_stage5c2g_exact_mobile_benchmark.py \
  --config configs/stage5c2g/exact_mobile_benchmark.yaml \
  --split calibration
python scripts/lock_stage5c2g_validity_tolerances.py \
  --calibration results/stage5c2g/calibration
```

Inspect only the calibration outputs. Do not inspect validation cases or tune their parameters.

## Experiment B untouched validation

```bash
python scripts/run_stage5c2g_exact_mobile_benchmark.py \
  --config configs/stage5c2g/exact_mobile_benchmark.yaml \
  --split validation
python scripts/analyze_stage5c2g_validity.py
```

## Experiment A fixed-hole-count ladder

Each command checkpoints by occupancy. Run one count at a time:

```bash
python scripts/run_stage5c2g_fixed_count.py --holes 3 --resume
python scripts/run_stage5c2g_fixed_count.py --holes 5 --resume
python scripts/run_stage5c2g_fixed_count.py --holes 7 --resume
python scripts/check_stage5c2g_invariants.py --require-actual
python scripts/analyze_stage5c2g_fixed_count.py
```

## Source decision, figures, report, and package

```bash
python scripts/make_stage5c2g_decision.py
python scripts/make_stage5c2g_figures.py
python scripts/make_stage5c2g_report.py
python scripts/make_stage5c2g_manifest.py --root . --out MANIFEST.stage5c2g.sha256
python scripts/verify_manifest.py --root . --manifest MANIFEST.stage5c2g.sha256
python scripts/package_stage5c2g_submission.py
```

Preserve an unedited terminal transcript, all attempt ledgers, calibration outputs, tolerance lock, validation outputs, and failed/resumed chunks.
