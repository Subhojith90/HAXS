# Stage 3B: Paired Finite-Size Mechanism Validation

Stage 3B should be run only after the Stage 3A DTWA validation repair passes. It does **not** attempt a constructive 3 dB recovery claim. It tests whether the repaired DTWA surrogate preserves the pre-registered mechanism-separation signal across multiple finite-size shapes and dimensions.

## Lite run

```bash
cd hole_aware_xxz_squeezing_engine_stage3b_paired_finite_size_mechanism
python -m pip install -e .
python scripts/run_tests.py
pytest tests/stage2 tests/stage3 tests/stage3a tests/stage3b tests/regression -q
python scripts/run_stage3b_all_lite.py
zip -r haxs_stage3b_lite_results.zip results/stage3b_lite figures/stage3b_lite manuscript/stage3b_lite
```

## Outputs

- `results/stage3b_lite/dtwa_validation/`
- `results/stage3b_lite/paired_finite_size/stage3b_finals.csv`
- `results/stage3b_lite/paired_finite_size/stage3b_paired_shape_effects.csv`
- `results/stage3b_lite/paired_finite_size/stage3b_dimension_summary.csv`
- `results/stage3b_lite/decision/stage3b_decision.json`
- `figures/stage3b_lite/paired_finite_size_core_effect.png`
- `manuscript/stage3b_lite/stage3b_report.md`

## Allowed claim if passed

After repairing the DTWA spin-length artifact, the lite paired finite-size surrogate continues to show a mechanism-separation signal across the tested shapes.

## Forbidden claims

- 3 dB constructive recovery
- no-go theorem
- exact quantum mobile-hole dynamics
- experimental realism beyond normalized surrogate units
- final publication-grade finite-size scaling
