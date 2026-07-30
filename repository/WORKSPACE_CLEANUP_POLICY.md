# Workspace cleanup policy

The workspace root contains only:

- `HAXS/`: the single active repository.
- `Archive/`: preserved historical working trees, transfer packages, and
  disposable runners.

Do not develop inside `Archive`. Do not create another repository for a new
execution. Create a `work/...` branch in `HAXS`, promote the accepted state to
a `release/...` branch, and add its workflow under `.github/workflows/`.

Execution outputs downloaded from GitHub should first be checked and recorded
under the matching `releases/<stage>/` directory. Redundant download and
transfer folders should then be moved to the dated workspace archive.
