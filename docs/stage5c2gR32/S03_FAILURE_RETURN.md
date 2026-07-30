# Stage 5C.2G-R3.2 pre-candidate S03 failure return

No R3.2 candidate was created. No G0, official G1, or downstream execution was
performed.

## Binding outcomes

- Phase 0: PASS (244 full tests; 60 targeted tests).
- S01 immutable failed-evidence reconstruction: PASS.
- S02 deterministic phase quadrature: PASS.
  - 4 physical case/occupancy units.
  - 4,096 quadrature nodes.
  - Maximum paired difference: 0.0.
  - Absolute sanity: PASS.
  - Time-step convergence: PASS.
- S03 preregistered statistical-sanity calibration: FAIL.
  - Benign trials: 1,024.
  - Benign false rejections: 0 (0%).
  - Upper 95% false-rejection interval: 0.3737404%.
  - Interval half-width: 0.1868702 percentage point.
  - Binding SESOI: 0.5% of the half-particle bound.
  - Binding-SESOI detections: 1,006/1,024 (98.2421875%).
  - Frozen power requirement: at least 99%.
  - Predeclared seed extension: not permitted because the interval-width
    trigger was not met.

Case-specific binding-SESOI detection:

- zero-hopping chain: 509/512 (99.4140625%);
- zero-spin-density rectangle: 497/512 (97.0703125%).

The primary Bonferroni rule therefore failed its frozen power criterion. The
candidate builder remains fail-closed because S03 is not `PASS`. The current
outputs must not be rerun, overwritten, extended, or retrospectively
rethresholded.

## Requested supervisory decision

Review the complete S01-S03 evidence and choose one prospective route:

1. restrict physical-sanity certification to deterministic quadrature for
   feasible small systems and abandon a broad stochastic certification claim;
2. authorize a newly preregistered replacement calibration with a scientifically
   justified rule, SESOI, or sampling design; or
3. stop the mechanism-validation route.

No route should reuse the failed S03 output as a new calibration sample.
