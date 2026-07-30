# HAXS Stage 2: Statistical Scaling and Mechanism Validation

This package extends the production HAXS engine with a Stage 2 evidence-amplification layer. It is designed to decide whether the current HAXS observations survive seed statistics, finite-size checks, mechanism ablation, parameter sensitivity, optimization cross-validation, and runtime scaling.

## Recommended first run: lite

```bash
cd hole_aware_xxz_squeezing_engine
python -m pip install -e .
python scripts/run_tests.py
pytest tests/stage2 -q
python scripts/run_stage2_all_lite.py
```

The all-lite runner executes:

```bash
python scripts/run_stage2_seed_statistics.py --config configs/stage2_lite/seed_statistics.yaml --out results/stage2_lite/seed_statistics
python scripts/run_stage2_finite_size.py --config configs/stage2_lite/finite_size.yaml --out results/stage2_lite/finite_size
python scripts/run_stage2_mechanism_ablation.py --config configs/stage2_lite/mechanism_ablation.yaml --out results/stage2_lite/mechanism_ablation
python scripts/run_stage2_parameter_sweep.py --config configs/stage2_lite/parameter_sweep.yaml --out results/stage2_lite/parameter_sweep
python scripts/run_stage2_cross_validation.py --config configs/stage2_lite/cross_validation.yaml --out results/stage2_lite/cross_validation
python scripts/run_stage2_runtime_scaling.py --config configs/stage2_lite/runtime_scaling.yaml --out results/stage2_lite/runtime_scaling
python scripts/make_stage2_decision.py --results results/stage2_lite --out results/stage2_lite/decision
```

## Full-scale commands

```bash
python scripts/run_stage2_seed_statistics.py --config configs/stage2_full/seed_statistics.yaml --out results/stage2_full/seed_statistics
python scripts/run_stage2_finite_size.py --config configs/stage2_full/finite_size.yaml --out results/stage2_full/finite_size
python scripts/run_stage2_mechanism_ablation.py --config configs/stage2_full/mechanism_ablation.yaml --out results/stage2_full/mechanism_ablation
python scripts/run_stage2_parameter_sweep.py --config configs/stage2_full/parameter_sweep.yaml --out results/stage2_full/parameter_sweep
python scripts/run_stage2_cross_validation.py --config configs/stage2_full/cross_validation.yaml --out results/stage2_full/cross_validation
python scripts/run_stage2_runtime_scaling.py --config configs/stage2_full/runtime_scaling.yaml --out results/stage2_full/runtime_scaling
python scripts/make_stage2_decision.py --results results/stage2_full --out results/stage2_full/decision
```

## Decision criteria

Do not claim constructive HAXS recovery unless cross-validated test improvement is consistently near or above 3 dB and does not collapse across seeds/folds.

Do not claim mechanism separation unless mobile-plus-spin-density curves separate from static-vacancy curves with stable bootstrap intervals and nontrivial distance across finite-size checks.

Do not claim no-go or threshold physics from Stage 2 unless the threshold boundary is nonzero, stable, and reproduced across the expanded grid.
