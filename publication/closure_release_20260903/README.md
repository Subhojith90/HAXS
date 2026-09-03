# HAXS publication-closure release — 3 September 2026

This directory is the complete, compact drafting handoff for Srinjoy. It is an
evidence release, not a claim that all originally planned scientific gates
passed.

## Start here

1. `EXECUTION_SUMMARY.md` — chronological record and final state.
2. `PAPER_INPUT_INDEX.md` — exact source for each number, table, and claim.
3. `CLAIM_BOUNDARY.md` — language that is supported or forbidden.
4. `EMAIL_TO_SRINJOY.md` — ready-to-send handoff message.
5. `RELEASE.json` — machine-readable identities and status.
6. `MANIFEST_SHA256.txt` — checksums for every release file other than itself.

## Evidence layout

- `evidence/stage5c2f/`: compact source-generated result report, gate tables,
  decision, hierarchy checks, runbook, and hashes. The raw result and clean
  source archives remain at `output/stage5c2f/` in the repository.
- `evidence/g0/`: complete Host-A and Host-B records, command records, JUnit,
  stdout, and two-host comparison. The 397 MB protocol is omitted here because
  its canonical split representation is already under `releases/stage5c2gR32A5/`.
- `evidence/g1/`: the complete official terminal return, structured receipt,
  setup/authorization/state records, transcript, and post-failure observability
  repair.
- `paper_inputs/`: supervisor-generated machine-readable tables for drafting.
- `supervisory/`: the final closure report, audit bundle, decision, and claim
  controls.

## Verify

From the repository root:

```bash
python3 scripts/verify_publication_closure_release.py
```

This verification is read-only and performs no scientific execution.
