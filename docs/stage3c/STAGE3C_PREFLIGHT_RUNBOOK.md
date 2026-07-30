# Stage 3C-preflight Runbook

Purpose: harden Stage 3A/3B before any large compute campaign.

This stage implements the exact supervisory blockers:

1. clean provenance and stale-output detection;
2. ED-DTWA spin-length and squeezing gates;
3. fixed-time mechanism inference as the primary metric;
4. best-over-time metric retained only as secondary;
5. nested uncertainty over disorder seeds and DTWA trajectory seeds;
6. fresh manifest, command template, report, and figures.

## Commands

```bash
python -m pip install -e .
python scripts/run_tests.py
pytest tests/stage2 tests/stage3 tests/stage3a tests/stage3b tests/stage3c tests/regression -q
python scripts/run_stage3c_preflight_all.py
zip -r haxs_stage3c_preflight_results.zip results/stage3c_preflight figures/stage3c_preflight manuscript/stage3c_preflight reproducibility/stage3c_preflight_manifest.json
```

## Stop/go logic

Do not proceed to full Stage 3C unless:

- stale-output detector passes;
- Stage 3A DTWA collapse gate passes;
- ED-DTWA short-time spin-length and squeezing gates pass;
- fixed-time core mechanism effects are negative in most shapes;
- fixed-time CI excludes zero for at least two shapes;
- nested trajectory uncertainty does not erase the effect in at least two shapes;
- manifest and command records are fresh.
