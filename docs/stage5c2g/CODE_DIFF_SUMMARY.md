# Stage 5C.2G Code-Diff Summary

## Protocol and provenance

- Added an immutable protocol candidate covering every Stage 5C.2G configuration, runner, analysis, test, exact-model source file, fixed-time definition, estimator, gate, runbook, and command file.
- Added external timestamp receipt finalization. Production runners refuse to start unless the receipt contains the current candidate SHA-256 and all covered hashes still match.
- Added a custody ledger for the frozen Stage 5C.2D confirmation and Stage 5C.2F source/results/submission archives.
- Removed block equivalence from Stage 5C.2G pass/fail logic.

## Random hierarchy and fixed-hole controls

- Added disjoint UUID-derived occupancy, path, and phase namespaces for exactly 3, 5, and 7 holes.
- Added checkpointed 16 x 6 x 4 paired blocks for every hole count.
- Added immutable occupancy/path/phase identifiers, actual occupancy and simulator-path hashes, parent and generating configuration hashes, and complete attempt ledgers.
- Added active bonds, largest occupied component, occupied-degree moments, hole clustering, boundary-hole fraction, and random-walk displacement descriptors.
- Locked the primary uncertainty estimator to an equal-occupancy 20,000-replicate nested cluster bootstrap. Balanced-ANOVA and occupancy-t intervals are secondary sensitivity estimators.

## Constrained spin-hole model

- Added a fixed-hole Hilbert space with local states hole/down/up and no double occupancy.
- Added nearest-neighbor XXZ exchange, spin-preserving hard-core particle hopping, and the hole-neighbor spin-density field.
- Particle hopping exchanges a hole with a neighboring spin and therefore transports the spin with the particle. The declared carrier convention is hard-core bosonic.
- Added sparse Krylov time evolution, collective-spin squeezing observables, exact particle accounting, quantum hole-density histories, and hole-configuration probabilities.
- Extended DTWA with an optional explicit initial occupancy so exact and surrogate cases start from identical hole configurations.

## Calibration and untouched validation

- Added separate calibration and untouched validation case lists.
- Calibration locks the maximum clean/static RMSE and verifies zero-hopping and zero-spin-density limits before validation can run.
- Untouched validation tests time-profile correlation, calibrated RMSE, sign agreement, component ranking, local-window sign, zero-coupling limits, norm, particle number, hole number, Hamiltonian Hermiticity, and hole-probability normalization.

## Decision and release controls

- Added source-generated four-way stop/go logic for both-pass, fixed-only, validity-only, and both-fail outcomes.
- Stage 5C3 production, Stage 5D, manuscript-result claims, public release, and exact mobile-hole mechanism claims remain false in every decision branch.
- Added figures, report generation, root-relative manifest generation, and separate clean-source/results packaging.
