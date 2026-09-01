# Stage 5C.2G-R3.2A.5 Acceptance Contract

This stage repairs the authorization lifecycle without modifying or exempting the immutable-root verifier.

## Required architecture

- The protocol/data root remains byte-identical after candidate construction.
- Receipt, authorization, setup, attempt state, transcripts and artifact manifests reside only in an external candidate-namespaced control root.
- Both roots reject symlinks and unlisted objects.
- Setup and environment verification complete before the sole official attempt is reserved.
- A single-writer transaction prevents receipt replay and concurrent reservation.

## Terminal local gate

The production finalizer, launcher and state code must complete exactly one valid receipt-to-runner-stub lifecycle. Wrong-candidate or stale authorization, replay, extra or missing control files, symlinks, setup failure, repeated launch, runner failure and invalid terminal evidence must fail closed.

No replacement candidate, physical Host A, physical Host B, receipt or official G1 is permitted until this local gate and the retained suites pass.
