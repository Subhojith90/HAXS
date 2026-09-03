# Stage 5C.2G-R3.2A.4 authoritative runbook

## Scope

This stage closes the production JUnit round trip and complete G0 return. It is
engineering-only. G1 and every downstream scientific gate remain blocked.

## Required order

1. Build `haxs-0.8.7` in the locked CPython 3.12.7 environment.
2. Write the A4 environment record and named-test ledger.
3. Run compileall, full tests and the A4 targeted suites while retaining raw
   JUnit XML and complete transcripts.
4. Run S01 production-command round-trip and adversarial acceptance tests.
5. Write adversarial outcomes and the exact-root manifest.
6. Build and package the new fail-closed candidate, then pass archive identity
   and strict fresh-unzip verification.
7. Run the complete local synthetic two-host return against that exact packaged
   protocol using production-format writer output. Preserve the raw host
   evidence and returned ZIP.
8. Verify that the dry-run decision binds the exact candidate and protocol
   archive before preparing any external-host release.
9. Run Host A and a physically distinct Host B G0 only after reviewing the
   local acceptance evidence. Stop and return the complete ZIP.

## Canonical entry points

```text
python -m pytest -q tests/stage5c2gR32A4/test_production_command_roundtrip.py
python -m pytest -q tests/stage5c2gR32A4/test_complete_return_closure.py
python -m pytest -q tests/stage5c2gR32A4/test_adversarial_acceptance_contract.py
python scripts/build_stage5c2gR32A4_candidate.py --fail-closed
python scripts/package_stage5c2gR32A4_protocol.py
python scripts/verify_stage5c2gR32A4_fresh_unzip.py --protocol <A4 protocol ZIP>
python scripts/dry_run_stage5c2gR32A4_complete_return.py --protocol <A4 protocol ZIP> --out <new dry-run root>
bash run_stage5c2gR32A4_G0.sh --host-label HOST_A
bash run_stage5c2gR32A4_G0.sh --host-label HOST_B
python scripts/package_stage5c2gR32A4_supervisor_return.py --host-a-root <HOST_A evidence> --host-b-root <HOST_B evidence> --protocol <A4 protocol ZIP> --out-dir <new directory>
```

## Stop conditions

Stop on the first failure. Never overwrite, delete, extend or select among
outputs. Never manually repair an extracted return. Preserve every failed
attempt under development history. A synthetic dry run never authorizes a
receipt or scientific execution.
