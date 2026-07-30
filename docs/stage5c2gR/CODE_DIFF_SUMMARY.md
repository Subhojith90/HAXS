# Stage 5C.2G-R defect-indexed repair summary

| Defect | Repair |
|---|---|
| D1 label-dependent path/phase streams | `physical_random_unit` derives occupancy/path/phase/state/block identities without label input; all labels reuse them. |
| D2 false zero-coupling failures | G1 runs paired exact and surrogate limits and requires full-curve equality within `1e-10 dB`. |
| D3 failed calibration still locks | G1, transport mapping, and tolerance scripts write `LOCKED.json` only on PASS; failures exit nonzero with `FAILED.json`. |
| D4 validation bypass | Validation runner requires cryptographically checked G1, mobility, and tolerance PASS locks before output creation. |
| D5 partial source lock | Candidate covers all local scientific Python, scripts, YAML configs, tests, Stage 5C.2G-R docs, and environment files. |
| D6 editable lock metadata trusted | Every runner reconstructs the full candidate payload and compares its SHA with candidate JSON and the external receipt. |
| D7 predecessor inputs absent | A formal content-addressed external-mount contract lists logical paths, immutable hashes, and `HAXS_CUSTODY_ROOT`; fresh unzip exercises it. |
| D8 `eta=t_h` assumption | Transport-only grid calibration fits eta using hole density, MSD, return probability, and configuration TV distance. |
| D9 single stochastic unit | Calibration and validation use multiple occupancies, paths, and phase batches and persist immutable unit IDs. |
| D10 stale resume/merge | Candidate-specific roots and hashed per-chunk manifests validate run IDs, row counts, file hashes, config/candidate hashes, and attempt completion. |
| D11 sign-only fixed-count rule | A `0.15 dB` practical threshold and simultaneous maximum-deviation bootstrap are preregistered. |
| D12 overstated topology/particle-statistics scope | Topology is exploratory; the comparator is explicitly hard-core bosonic and cannot support exact lithium-6 language. |

