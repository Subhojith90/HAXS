# Stage 5C.2G-R3.2 runbook

This runbook is fail-closed. Run one numbered phase at a time and inspect its
terminal output before continuing. Do not delete, overwrite, or select among
failed or ambiguous outputs.

## Frozen statistical choices

- Complete deterministic CSS-x quadrature: 1,024 equally weighted nodes for
  five active spins.
- Four unique case/occupancy units; phase nodes are not replicates.
- Integration refinement: one, two, and four RK4 substeps per output interval.
- Stochastic calibration primary rule: one-sided Bonferroni simultaneous
  normal envelope at familywise alpha 0.01.
- Calibration: 512 benign seeds per case (1,024 total).
- Binding SESOI: 0.5% of the physical half-particle bound. This is frozen
  before calibration; 0.25% and 1% are secondary sensitivity points.
- Pass targets: false rejection <=1%, upper 95% interval <=1.5%, binding-SESOI
  detection >=99%, and Monte Carlo interval half-width <=0.5 percentage point.

## Dependency order

1. Static compilation and tests.
2. S01 immutable failed-evidence reconstruction.
3. S02 deterministic quadrature and time-step refinement.
4. S03 statistical-sanity calibration.
5. Build the non-editable 0.8.2 wheel.
6. Build and package the R3.2 candidate.
7. Run G0 on two physically distinct hosts.
8. Return the supervisor-review package.
9. Stop. A new receipt is required before one official G1.

## Prohibited actions

- Do not retry R3.1 or reuse its receipt.
- Do not change a threshold after looking at S02 or S03.
- Do not create a candidate if S01, S02, or S03 is not `PASS`.
- Do not run official G1 before the new two-host review and receipt.
- Do not run G2-G4, Stage 5C3, Stage 5D, or make manuscript/public claims.

Exact shell commands are maintained in `STAGE5C2GR32_COMMANDS.sh`.
