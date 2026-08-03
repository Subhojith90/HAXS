# R3.2A to R3.2A.1 repair summary

The replacement stage implements the exact narrow repair authorized by the
2026-07-30 supervisory decision:

- exact-key current-stage structured-receipt schema;
- current-stage finalizer bound to candidate, protocol, runtime, wheel,
  environment, configuration, plan, unit registry, runner, named tests and
  two-host G0;
- isolated installed-wheel G1 runner and launcher;
- atomic create-once G1 state with terminal fail-closed handling;
- explicit predecessor receipt, lock, state and launcher rejection;
- exact root manifest, named-test ledger and strict fresh-unzip verifier;
- inclusion of the five formerly injected root files and seven predecessor
  custody objects in the protocol itself;
- adversarial receipt, replay, archive, stale-state and multiprocess-race
  tests;
- replacement Host-A and GitHub Host-B G0 workflows with no post-extraction
  repository reconstruction;
- JUnit XML and content-addressed return packaging.
- predecessor security tests retained, with repository-root inspection and
  immutable-wheel checks redirected to the exact R3.2A.1 runtime contract;
  the initial development failure remains preserved in the protocol history.

Candidate `1950c01d...c165` remains immutable, accepted only as an
infrastructure milestone, and is not executable under this repair.
