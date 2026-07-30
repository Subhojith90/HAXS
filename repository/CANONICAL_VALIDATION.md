# Canonical repository validation

Validated on 2026-07-30 from a fresh extraction of the immutable R3.2A
protocol archive, with the manifest-bound custody objects, root contracts,
offline wheelhouse, and bound CPython 3.12.7 runtime supplied by this
repository.

- Full test suite: `254 passed`
- R3.2A/R3.2/R3/regression targeted suite: `70 passed`
- Immutable installed-wheel gate: `PASS`
- Fresh-unzip content gate: `PASS` (`679` content files)
- Candidate SHA-256:
  `1950c01dfd46f4c381e2d333dbd2c3bce1969b65140689961662c287dd54c165`
- Protocol archive SHA-256:
  `b60cbfa1f5296d2d7844f4324d21b0b6743f2d10b93f373be1484e3fe79ae694`

This validation is G0/pre-execution verification only. It did not execute G1
or any downstream scientific stage. Host-B G0 and two-host comparison remain
pending until the GitHub workflow is manually dispatched from the immutable
release branch.
