# Execution summary

## Scientific result retained for drafting

Stage 5C.2F tested a selected 3x3x3 stochastic moving-occupancy surrogate. The
contrast is defined as `static-only - mobile-plus-spin-density` in dB.

| Block | Mean effect (dB) | Hierarchical SE (dB) | 95% interval (dB) | Negative occupancy units |
|---|---:|---:|---:|---:|
| Primary | -0.411797 | 0.048709 | [-0.517604, -0.307798] | 16/16 |
| Confirmation | -0.474424 | 0.039405 | [-0.571780, -0.376832] | 12/12 |

The primary-confirmation difference was 0.062627 dB with a 90% equivalence
interval of [-0.044247, 0.169500] dB against a preregistered ±0.25 dB margin.
All 768 primary simulation attempts completed and none failed.

Interpretation: within this selected surrogate, the mobile-plus-spin-density
condition produced better squeezing than the static-only condition under the
frozen contrast convention. This is not evidence for microscopic lithium-hole
dynamics or a universal mobile-hole mechanism.

## Reproducibility and custody

The final A5 candidate was
`481ca1905bedc68d6ac3eb36ac61b80356d4e32cf8847b3e927f081201240932`.
Its protocol archive was
`d804a203567419f4775fb1d7357cfd9675563ba31068bc10918b9d27f2e1f70f`.

G0 passed independently on two physically distinct hosts. Each host recorded
402 full and 169 targeted passing tests with zero failures or skipped tests.
The two-host comparison contained no identity mismatches or forbidden state and
has SHA-256
`9745c61a7bbb358472f6d64832af48823686cad1af712e6ddefb3965b6008154`.
No A5 scientific execution occurred during G0.

## Official G1 terminal event

Srinjoy issued receipt `f8035d48-a73c-49b1-bf60-872983b24d62`, authorising one
G1 attempt only. The receipt was bound to the candidate, protocol, environment,
runner, configuration, plan, unit registry, test ledger, and two-host G0 return.

The official attempt `52e6f14b27a2474ba6db70755825d893` ran exactly once and
terminated `FAILED` with runner exit status 1. The artifact manifest contains no
scientific files. The frozen launcher retained only the wrapper exception, so
the preserved record cannot determine whether the child failed a scientific
predicate or encountered a runtime defect. The attempt is consumed and must not
be rerun. G2-G4 were not run.

After terminalization, development-only tests added failure-transcript and
partial-output preservation; 17 focused A5 tests passed. That repair was not
part of the consumed candidate and does not retroactively alter its evidence.

## Publication status

The repository is ready as a transparent drafting record for a narrow surrogate
or methods/negative-result paper. A manuscript claiming validated exact-carrier
physics is not supported. The supervisor's last plan called for M01 transport
calibration and M02 untouched exact-surrogate validity/failure-boundary work;
neither is represented as completed in this release.
