# Stage 5C.2G-R2 runbook

Stage 5C.2G-R2 is a protocol-hardening iteration. No simulation is authorized before its replacement candidate is externally timestamped. After timestamping, G1 alone may run and must return for supervisory review. G2-G4 remain blocked.

## Canonical configuration and plan identity

Every gate has exactly one canonical configuration path in `configs/stage5c2gR2/protocol.yaml`. Scientific runners accept no free-form configuration or output paths. The candidate binds each configuration SHA-256 and the complete deterministic expected-ID plan SHA-256 and row count.

G1 contains exactly 128 comparison rows. G2, G3, and G4 plans contain 6656, 512, and 2304 rows respectively, but their executables exit nonzero until separate authorization.

## Exact runtime file set and environment

The candidate records the exact set and hash of every local Python, YAML, JSON, shell, TOML, lock, text, and Markdown runtime-readable file outside excluded result/output/cache/archive roots. Addition, deletion, or modification changes candidate identity and fails against the external receipt.

The supported reference environment is CPython 3.12 with NumPy 1.26.4, pandas 2.2.2, SciPy 1.13.1, matplotlib 3.9.2, PyYAML 6.0.1, and pytest 7.4.4. Candidate construction and every runner enforce these versions.

## Atomic gate state

Each gate has one state file: `results/stage5c2gR2/state/GATE.json`. Starting a new attempt atomically replaces any prior PASS with RUNNING. Completion replaces RUNNING with PASSED or FAILED. Therefore, a failure or interrupted rerun cannot leave an older PASS authoritative.

State identity includes candidate SHA, canonical-config SHA, expected-plan SHA, attempt ID, raw-manifest SHA, and a recomputed state digest.

## Raw evidence and authorization

Every attempt uses a candidate/config/attempt-specific artifact root. Its manifest records exact expected and observed IDs, row counts, and SHA-256 for every raw file. Verification rejects missing, extra, duplicate, stale, or modified evidence.

Supervisor authorization never trusts a supplied gate digest. It reconstructs the current candidate, canonical config and plan, atomic state, raw manifest, raw file hashes, attempt ID, and exact file set before checking that the external receipt binds those recomputed values.

## Hierarchical validity

The Stage 5C.2G-R2 estimator performs nested occupancy/path/phase resampling. It produces confidence intervals for every decision metric rather than setting a `hierarchical_units_reported` Boolean. Joint resampling uses the same nested draws across nearby times, preserving time covariance for simultaneous inference. G3 remains blocked, but the estimator and synthetic coverage/regression tests are part of G0.

## Legacy routes

The rejected Stage 5C.2G and Stage 5C.2G-R finalizers and scientific runners exit nonzero with replacement-stage messages. Rejected candidates `e9a974...` and `e65745...` cannot be finalized or officially executed.

