# HAXS branch and release policy

This is the only active HAXS repository.

## Branches

- `main`: stable repository structure, documentation, and accepted releases.
- `release/stage5c2g-r32a`: immutable R3.2A candidate, evidence, and G0 workflow.
- `work/<stage-or-repair>`: future development branches.
- A new repository is never created for a new execution.

Each candidate-changing repair starts from `main` on a `work/...` branch.
After tests and supervisory approval, merge or fast-forward it to a named
`release/...` branch. GitHub Actions must be dispatched from the exact release
branch and commit recorded in the return artifact.

## Repository layout

- `src/`, `scripts/`, `configs/`, `tests/`, `docs/`: working scientific source.
- `results/`, `output/`: candidate-bound evidence included by the protocol.
- `releases/<stage>/`: immutable protocol ZIP, checksum, and release metadata.
- `ci/frozen/<stage>/`: exact offline runtime, dependencies, and reference host.
- `.github/workflows/`: all present and future GitHub workflows.
- `repository/`: operating policy and current-release index.

Superseded local transfer folders and one-off runner repositories belong in the
workspace-level `Archive`, never beside this repository.
