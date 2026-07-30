# HAXS Stage 5C.2G-R3.1 Authorization Re-lock

## Current development stage: Stage 5C.2G-R3.1

Stage 5C.2F remains accepted as an internal target-shape hierarchy/statistical re-lock. The active patch implements Stage 5C.2G-R3.1 Absolute-Sanity, Import-Isolation, Root-Containment, and Structured-Receipt Re-lock. All preceding G, G-R, G-R2, and G-R3 candidates are rejected. See `docs/stage5c2gR3/STAGE5C2GR3_RUNBOOK.md` and `STAGE5C2GR3_COMMANDS.sh`.

R3.1 is a pre-execution protocol candidate. Do not issue a receipt and do not run G1 until the supervisor accepts the R3.1 two-physical-host G0 package. After acceptance and a new exact structured receipt, G1 alone may run and must return for review. G2-G4, Stage 5C3 production, Stage 5D, manuscript-result claims, public release, and exact lithium mobile-hole claims remain blocked.

The accepted Stage 5C.2F scientific evidence is preserved as predecessor custody. R3 changes authorization, evidence verification, concurrency control, runtime identity, installation, and environment reproducibility; it makes no new scientific claim.

## Immutable setup

```bash
python -m pip install --require-hashes -r requirements-stage5c2gR3.lock
python -I scripts/verify_stage5c2gR3_immutable_install.py
```

Editable installation is forbidden because it mutates source-tree package metadata. Wheels are built from an external temporary copy and installed outside the candidate tree.

## R3.1 G0 only

```bash
python -I scripts/check_stage5c2gR3_static_gate.py
python scripts/run_tests.py
python -I scripts/verify_stage5c2gR3_protocol.py --custody-root "$HAXS_CUSTODY_ROOT"
```

## Custody contract

`HAXS_CUSTODY_ROOT` must point to a read-only external tree containing the seven predecessor objects declared in `configs/stage5c2gR3/custody.yaml`. Custody content is verified by SHA-256 and is not embedded or modified.

## Claim boundary

Allowed: R3.1 checks whether one pre-execution protocol object is semantically fail-closed, serializable, completely identified, immutable under setup, and reproducible on two physically distinct locked hosts.

Forbidden: Stage 5C3 production approval, Stage 5D compute, publication-readiness claims, exact mobile-hole dynamics, component-mechanism claims, or finite-size scaling claims.
