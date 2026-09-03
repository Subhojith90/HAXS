# Release process

The canonical repository is `Subhojith90/HAXS`. Development is consolidated on
one repository; no new repository is required for this handoff.

1. Merge the reviewed closure commit into `main` by fast-forward.
2. The `Publication closure integrity` workflow verifies all compact evidence,
   identities, JUnit semantics, G1 terminal state, and the release manifest.
3. The workflow builds `HAXS_Publication_Closure_20260903.zip` directly from the
   committed Git tree and uploads it with a SHA-256 sidecar.
4. Send Srinjoy the GitHub commit/workflow link and the downloaded workflow
   artifact, using `EMAIL_TO_SRINJOY.md`.
5. Do not create a public GitHub release or DOI from this record unless Srinjoy
   separately clears public software release. Repository publication and
   scientific claim authorization are distinct decisions.

The historical A5 Host-B workflow is not triggered by this merge because it is
scoped to `release/stage5c2g-r32a5`. No G0 or G1 execution occurs in the
publication-closure workflow.
