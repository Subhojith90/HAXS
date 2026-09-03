# Stage 5C.2G-R3.2A.3 Frozen Acceptance Contract

R3.2A.3 is a narrow authorization repair. It does not alter or execute the scientific protocol.

Authorization requires exact ordered JUnit testcase equality with the candidate-bound ledgers, zero skipped/failed/errored cases, exact structured command records with zero exit status, transcript-to-JUnit binding, and equality of both host claims to the SHA-256 of the protocol archive actually supplied to the finalizer.

Only the genuine complete fixture may reach `VALIDATED_DRY_RUN`. Every invalid fixture in `configs/stage5c2gR32A3/adversarial_fixture_ledger.json` must fail before receipt, lock, setup state, or scientific-attempt state creation.

Candidate `24d6d3eb09b41feef6ef8858a300fc0ecbc9c9cf562bdc363d370ff528f2c9a4` is permanently ineligible for a receipt or G1 execution. Its two-host return is preserved only as provisional G0 evidence.
