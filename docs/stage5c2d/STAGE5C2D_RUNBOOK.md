
# Stage 5C.2D Runbook

Stage 5C.2D repairs the random hierarchy before any Stage 5C3 or Stage 5D compute.
It separates occupancy, mobile-hole path, and DTWA phase-batch seeds and runs a two-label
3x3x3 primary/confirmation relock.

Run:

```bash
python -m pip install -e .
python scripts/run_tests.py
PYTHONPATH=src pytest tests/stage5c2d tests/random_effects tests/regression -q
python scripts/run_stage5c2d_all.py --dry-run
python scripts/run_stage5c2d_all.py
python scripts/make_stage5c2d_manifest.py --root . --out MANIFEST.sha256
```

Stage 5D remains blocked. Stage 5C3 data production is allowed only if Stage 5C.2D passes both primary and confirmation gates.
