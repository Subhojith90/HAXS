# Stage 5C.2G-R3.2 supersession policy

Stage 5C.2G-R3.1 candidate
`91344d090d9f3387781c4e53bbbe4a5c9b359eaa82f47373b2d4f55cfcf2a2a3`
remains an immutable failed candidate.

Its single official attempt
`83809c41b55e453599953c9379623088` remains `FAILED`. Its receipt
`bec6a297-cf01-4df4-868f-1e01110167dd` is exhausted and cannot authorize
another execution.

R3.2 does not reinterpret, repair in place, or retry R3.1. It supersedes the
decision design by:

1. independently reconstructing the failed evidence (S01);
2. using complete CSS-x phase quadrature for small limiting cases (S02);
3. calibrating a separate uncertainty-aware rule for later stochastic gates
   (S03); and
4. creating a new candidate identity only after S01-S03 pass.

G1 remains blocked until two physically distinct G0 hosts reproduce the new
candidate, the supervisor accepts it, and a new exact G1-only structured
receipt is issued. G2-G4 and all publication-result scopes remain blocked.
