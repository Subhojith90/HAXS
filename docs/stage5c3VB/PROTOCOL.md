# Stage 5C.3-VB exact-surrogate domain-of-validity and failure-boundary protocol

Status: DESIGN ONLY - SCIENTIFIC EXECUTION BLOCKED.

## Primary question

After calibrating stochastic mobility using transport observables only, does the
frozen stochastic moving-occupancy surrogate preserve squeezing direction,
mechanism-component ranking and time-profile behavior on untouched constrained
exact/Krylov one- and two-hole cases?

## Separation of data

- M01 calibration cases determine the mobility map from hole-density
  propagation, mean-square displacement, return probability and
  configuration-distance observables only.
- Squeezing, component ranking and squeezing time profiles are forbidden during
  calibration and model selection.
- M02 validation cases remain untouched until the mobility map, tolerances,
  multiplicity correction and ambiguity rules are frozen and timestamped.
- M03 contains separate two-hole, fixed-count and topology controls.
- B01/B02 held-out geometries and dimensions are not used for boundary fitting.

## Prespecified comparisons

1. constrained exact/Krylov microscopic dynamics;
2. frozen stochastic moving-occupancy surrogate;
3. static-hole/no-motion control;
4. deliberately misspecified low- and high-mobility controls;
5. hole-count-only, connectivity-only and static-dilution baselines;
6. mobile-only, spin-density-only, combined and everything component labels.

## Primary validation endpoints

- transport discrepancy under the frozen M01 mapping;
- sign agreement of the prespecified squeezing contrast;
- mobile-only versus spin-density-only component ranking;
- full time-profile discrepancy rather than a selected time point;
- uncertainty across physical initial conditions and stochastic units;
- held-out boundary classification beyond trivial baselines.

Exact numerical SESOIs, tolerances, familywise error control, case registries,
seed namespaces and ambiguous-zone rules must be populated and externally
timestamped before any M01/M02 row is executed.

## Decision rules

- Rescue: untouched sign, component ranking and time-profile criteria all pass
  without squeezing-based recalibration, supporting a restricted validated
  surrogate domain.
- Failure-boundary pivot: untouched validity fails but the failure region is
  stable and predictively separable on held-out cases.
- Terminate mechanism wording: untouched validity fails and no stable boundary
  beats hole-count, connectivity or static-dilution baselines.

Failure of M02 immediately terminates exact-mobile-hole wording. No result from
this protocol may be described as lithium mobile-hole dynamics unless the
microscopic comparator gate passes.
