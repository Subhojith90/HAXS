# Stage 5C.2G-R3.2A runbook

Use CPython 3.12 and the frozen dependency lock. Every evidence command writes to a new path and
refuses overwrite.

1. Compile and run the full and targeted tests.
2. Run `run_stage5c2gR32A_phase_quadrature.py`.
3. Run the non-authorising development comparison.
4. Open the untouched validation exactly once with the frozen rule.
5. Build the immutable wheel.
6. Build the fail-closed candidate and protocol archive.
7. Verify the protocol from a fresh unzip.
8. Stop. G0 requires two physically distinct hosts. Official G1 requires a new structured receipt.

Host commands:

`python -I scripts/run_stage5c2gR32A_g0.py --host-label HOST_A --out results/stage5c2gR32A/g0/HOST_A.json`

`python -I scripts/run_stage5c2gR32A_g0.py --host-label HOST_B --out results/stage5c2gR32A/g0/HOST_B.json`

Compare only after both returns exist:

`python -I scripts/compare_stage5c2gR32A_g0_hosts.py --host-a results/stage5c2gR32A/g0/HOST_A.json --host-b results/stage5c2gR32A/g0/HOST_B.json --out results/stage5c2gR32A/g0/TWO_HOST_G0.json`

The failed R3.2 S03 directory is immutable predecessor evidence and must never be deleted, rewritten,
extended, or used for rule selection.
