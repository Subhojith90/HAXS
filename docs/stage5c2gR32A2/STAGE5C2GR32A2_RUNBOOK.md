# Stage 5C.2G-R3.2A.2 runbook

## Stop rules

- Never overwrite an output, transcript, candidate, protocol, Host record or return archive.
- Stop on the first nonzero status and preserve all evidence.
- Do not create a supervisor receipt and do not run G1 in this iteration.
- Host A and Host B must be physically distinct.

## Required order

1. Build the immutable `haxs-0.8.5` wheel in an exact CPython 3.12.7 environment populated only from the frozen wheelhouse.
2. Write the environment attestation, named-test ledger and exact root manifest.
3. Run compileall, the full suite and `tests/stage5c2gR32A2` targeted suite.
4. Run the root/environment adversarial fixtures and confirm that authorization, receipt, lock and G1 state remain absent.
5. Build a new candidate, package it, and pass strict fresh-unzip verification.
6. Run Host-A G0 from a fresh extraction. Freeze its complete evidence root.
7. Prepare the single-repository GitHub release inputs and run Host-B G0 on the release branch.
8. Package the canonical complete G0 return; send it for separate review.

The canonical command entry points are:

```text
python -I -m pytest -q tests/stage5c2gR32A2/
python -I scripts/verify_stage5c2gR32A2_root.py --root <fresh-protocol-root>
python -I scripts/verify_stage5c2gR32A2_environment.py --root <fresh-protocol-root>
python -I scripts/build_stage5c2gR32A2_candidate.py --fail-closed
bash run_stage5c2gR32A2_G0.sh --host-label HOST_A
bash run_stage5c2gR32A2_G0.sh --host-label HOST_B
python -I scripts/compare_stage5c2gR32A2_g0_hosts.py --host-a HOST_A.json --host-b HOST_B.json --evidence-root <return-root> --out TWO_HOST_G0.json
python -I scripts/package_stage5c2gR32A2_supervisor_return.py --host-a-root <host-a-evidence> --host-b-root <host-b-evidence> --protocol <protocol.zip> --out-dir <deliverables>
```
