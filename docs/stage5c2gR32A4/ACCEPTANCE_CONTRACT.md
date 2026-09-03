# Stage 5C.2G-R3.2A.4 frozen engineering acceptance contract

R3.2A.4 is the final planned protocol-only repair. It performs no scientific
execution and cannot authorize G1.

## Required pass conditions

1. A command record emitted by the production G0 writer passes the production
   verifier under arbitrary safe absolute roots, including roots with spaces.
2. The recorded relative JUnit path and executed absolute or relative
   `--junitxml=` target resolve to one canonical file inside the evidence root.
3. Missing, duplicate, malformed, outside-root, noncanonical, missing and
   symlinked JUnit targets fail before receipt, lock, state or attempt creation.
4. All retained A3 adversarial fixtures continue to fail closed.
5. A local synthetic Host-A/Host-B return is built from production-format raw
   JUnit XML and structured command records and passes complete-return
   reconstruction after a fresh unzip.
6. The official finalizer accepts a single safe ZIP only. Synthetic dry-run
   returns are permanently ineligible for a receipt.
7. The protocol rebuild is byte-identical and all executable/importable inputs,
   packagers, manifests, ledgers and runbooks are candidate-bound.
8. Authoritative full and targeted suites pass under the locked Darwin ARM64
   CPython 3.12.7 profile and their raw evidence is retained.

## Frozen stop rule

After these conditions pass, another protocol-only candidate is permitted only
after demonstrating a concrete route to evidence corruption, unbound executable
influence, false scientific attribution, blocked-scope bypass, or loss or
misclassification of the sole official attempt. Otherwise the project proceeds
to the supervised scientific gate chain.

## Prohibited actions

- Do not patch candidate `03e02b4bc98a5fd116442b8453d8cf2f533c5f66c36a5b7868045d91b320f528`.
- Every production-format G0 writer and complete-return packager invocation,
  including the local synthetic acceptance run, must execute from a fresh
  extraction of the exact candidate-bound protocol rather than a Git checkout.
- The isolated `compileall` command must route bytecode through an explicit,
  canonical `-X pycache_prefix=...` argument to a host-labelled external
  diagnostics directory; environment-only routing is insufficient under `-I`.
  Validation is independent of whether the evidence root itself is host-named
  or is the physical wrapper's shared `evidence` directory.
- Do not treat a synthetic return as physical two-host G0 evidence.
- Do not issue a receipt or run G1 before replacement physical two-host G0 and
  separate supervisory acceptance.
- Do not execute Stage 5C.3-VB scientific rows during A4.
