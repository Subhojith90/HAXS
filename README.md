# Hole-Aware XXZ Screening (HAXS)

This repository is the canonical code, custody, and publication-input record for
the HAXS project.

## Current outcome

- Stage 5C.2F produced a replicated negative `static-only - mobile-plus-spin-density`
  contrast for one selected 3x3x3 stochastic moving-occupancy surrogate.
- Stage 5C.2G-R3.2A.5 G0 passed on two physically distinct hosts: 402 full and
  169 targeted tests passed on each host.
- The single authorised A5 G1 attempt terminated `FAILED` before producing any
  scientific files. It must not be rerun under the consumed receipt.
- G2-G4, exact mobile-hole claims, causal mechanism claims, and universal
  no-go claims remain unsupported.

The drafting handoff is in [`publication/closure_release_20260903`](publication/closure_release_20260903/README.md).
It contains the compact evidence, paper-ready tables, claim boundary, execution
summary, final supervisory record, checksums, and an exact email to the
supervisor.

## Frozen A5 identities

- Candidate SHA-256: `481ca1905bedc68d6ac3eb36ac61b80356d4e32cf8847b3e927f081201240932`
- Protocol archive SHA-256: `d804a203567419f4775fb1d7357cfd9675563ba31068bc10918b9d27f2e1f70f`
- Two-host G0 SHA-256: `9745c61a7bbb358472f6d64832af48823686cad1af712e6ddefb3965b6008154`
- Official G1 attempt: `52e6f14b27a2474ba6db70755825d893` (`FAILED`)

The large protocol is stored as checked split parts under
`releases/stage5c2gR32A5/`. Reconstruct it only when protocol-level reproduction
is needed; the publication release deliberately avoids a second 397 MB copy.

## Verify the publication release

```bash
python3 scripts/verify_publication_closure_release.py
```

The GitHub workflow `Publication closure integrity` runs the same standard-library
verification on `main`. It performs no scientific execution.

## Claim boundary

Allowed: a replicated negative contrast within the selected stochastic
moving-occupancy surrogate, together with the documented two-host G0
reproducibility result.

Not allowed: exact lithium mobile-hole dynamics, a causal mobile-hole mechanism,
a universal no-go result, constructive 3 dB recovery, cross-dimensional
generalisation, or a claim that the failed G1 attempt is a scientific null result.
