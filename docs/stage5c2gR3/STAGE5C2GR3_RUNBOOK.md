# Stage 5C.2G-R3.1 pre-execution runbook

R3.1 is a narrow authorization repair. G0 may run; scientific G1 remains blocked. The same reconstructed candidate must pass G0 on two physically distinct clean CPython 3.12.7 / Darwin arm64 hosts before it is returned for supervisory acceptance.

## Scientific predicate

G1 can pass only when both independent analyzers derive paired equality and absolute physical sanity from candidate-bound raw curves. The sanity layer checks initial coherent-state identities, particle and hole conservation, normalization, component and spin-length bounds, positive finite squeezing and variance, dB consistency, the Wineland identity, topology-compatible active-bond counts, and nontrivial time evolution. Paired zero curves and paired constant-999 curves fail.

## Import and execution isolation

Authorization entry points require Python isolated mode (`-I`) and reject dangerous import/preload environment variables. The immutable-install gate builds a deterministic wheel from an external copy, installs it outside the source tree, records its SHA-256, checks module origins and native libraries, and proves that installation did not mutate the candidate. The only official G1 entry point is `scripts/launch_stage5c2gR3_G1_isolated.py`; it installs the candidate-bound wheel in a temporary target and refuses source/config/output overrides.

After supervisory acceptance, finalization and G1 must occur in a fresh extraction of the accepted protocol ZIP, never in the historical development checkout. The protocol lock enforces this minimal top-level root and rejects development folders or any other extra entry.

## Root and evidence containment

The complete top-level preparation root is deny-by-default. Repository-root hooks, unexpected entries, native/loadable artifacts, hidden paths, generated installation metadata, and symlinks are rejected. Evidence is confined to one candidate/config/gate/attempt root. The evidence root and every ancestor are checked lexically for symlinks and opened no-follow. The recursive manifest rejects absolute paths, traversal, nesting, missing or extra files, and changed digests.

## Structured receipt

Free text is never authorization. After supervisor acceptance, the supervisor must issue JSON matching `configs/stage5c2gR3/structured_receipt_template.json` exactly. It binds the new candidate, runtime tree, protocol archive, exact `G1_ONLY` scope, and every downstream block. Negated or ambiguous language cannot validate.

## Two physical hosts and transcripts

Each host writes a hardware attestation containing one-way hashes of its macOS platform UUID and serial number. The comparison gate requires both hardware hashes to differ while candidate, wheel, configuration, plan, runtime, and environment specification identities agree. Two virtual environments on one machine fail this gate.

Only the nine final transcript names listed in `configs/stage5c2gR3/protocol.yaml` are authoritative. Retry and development logs remain outside the supervisor-review ZIP.

## Permissions

- G0 and packaging: approved.
- External receipt and G1: blocked until the R3.1 candidate is accepted.
- G2-G4, Stage 5C3, Stage 5D, manuscript-result claims, exact lithium mobile-hole claims, and public release: blocked.
