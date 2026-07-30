# HAXS Stage 3: Publication Evidence Generation

Stage 3 upgrades the Stage 2 mechanism-candidate package into a publication-evidence campaign. It does not assume that the mechanism claim is true. It measures whether the mechanism separation survives larger seed statistics, finite-size checks, bootstrap confidence intervals, pairwise statistical tests, and cross-validation.

## Lite run

Use this first on a laptop:

```bash
cd hole_aware_xxz_squeezing_engine_stage3_publication_evidence
python -m pip install -e .
python scripts/run_tests.py
pytest tests/stage2 tests/stage3 -q
python scripts/run_stage3_all_lite.py
```

Expected output roots:

```text
results/stage3_lite/seed_campaign
results/stage3_lite/finite_size
results/stage3_lite/mechanism_inference
results/stage3_lite/crossval_inference
results/stage3_lite/decision
figures/stage3_lite
manuscript/stage3_lite/stage3_report.md
```

## Full run

The full run is intentionally heavier. Execute module-by-module:

```bash
python scripts/run_stage3_seed_campaign.py --config configs/stage3_full/publication_evidence.yaml --out results/stage3_full/seed_campaign
python scripts/run_stage3_finite_size.py --config configs/stage3_full/publication_evidence.yaml --out results/stage3_full/finite_size
python scripts/run_stage3_mechanism_inference.py --config configs/stage3_full/publication_evidence.yaml --out results/stage3_full/mechanism_inference
python scripts/run_stage3_crossval_inference.py --config configs/stage3_full/publication_evidence.yaml --out results/stage3_full/crossval_inference
python scripts/make_stage3_figures.py --results results/stage3_full --out figures/stage3_full
python scripts/make_stage3_decision.py --results results/stage3_full --out results/stage3_full/decision
python scripts/make_stage3_report.py --results results/stage3_full --figures figures/stage3_full --out manuscript/stage3_full
```

## Claim gates

Constructive recovery is allowed only if the cross-validation lower confidence bound clears the agreed target. The default target remains 3 dB.

Mechanism-paper language is allowed only if pairwise mechanism inference remains significant at full scale and finite-size trends do not reverse.

No-go language is not allowed from this package. At most, Stage 3 can motivate a later restricted empirical-boundary stage.

## Zip results for audit

```bash
zip -r haxs_stage3_lite_results.zip results/stage3_lite figures/stage3_lite manuscript/stage3_lite
```

For full run:

```bash
zip -r haxs_stage3_full_results.zip results/stage3_full figures/stage3_full manuscript/stage3_full
```
