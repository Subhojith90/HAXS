# Stage 3A: DTWA Validation Repair and Paired Mechanism Rerun

This package is the targeted repair iteration requested by the supervisory audit.
It is **not** a full-scale campaign.

## Scientific purpose

Stage 3A fixes the DTWA initialization/normalization convention that produced an artificial first-step spin-length collapse in Stage 3 Lite. It then reruns the repaired-lite mechanism and cross-validation analyses with paired mechanism statistics.

## Main repair

The DTWA CSS-x phase-point sampler uses `(Sx,Sy,Sz)=(1/2, ±1/2, ±1/2)`. The previous RK4 step renormalized every phase point to length `1/2`, causing the first-step collapse toward `1/sqrt(3)`. The repaired RK4 step preserves each trajectory/site phase-point norm from the previous step instead of forcing a spin-1/2 vector norm.

## Run commands

```bash
cd hole_aware_xxz_squeezing_engine_stage3a_dtwa_validation_repair
python -m pip install -e .
python scripts/run_tests.py
pytest tests/stage2 tests/stage3 tests/stage3a tests/regression -q
python scripts/run_stage3a_all_lite.py
```

## Package results for supervisory audit

```bash
zip -r haxs_stage3a_lite_results.zip results/stage3a_lite figures/stage3a_lite manuscript/stage3a_lite
```

## Pass/fail interpretation

Proceed to Stage 3B only if:

1. `results/stage3a_lite/dtwa_validation/dtwa_validation_summary.csv` has all gates passed.
2. There is no first-step spin-length collapse to approximately `0.577`.
3. CSS squeezing at `t=0` is near `0 dB` within trajectory sampling tolerance.
4. The paired static-only vs mobile-plus-spin-density mechanism signal survives the repaired-lite rerun.

Do not run full-scale studies if the DTWA validation gate fails.


## Lite repair config

The all-lite command uses `configs/stage3a_lite/publication_evidence_repair.yaml`, which is intentionally smaller than the Stage 3 full/lite package so that the validation repair can be checked before spending compute.
