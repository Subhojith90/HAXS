#!/usr/bin/env zsh
# REFERENCE COMMANDS ONLY. Run one phase manually and inspect its output.

set -o pipefail

ROOT="/Users/subhojithalder/Desktop/Research Papers/Hole Aware XXZ Screening/haxs_stage5c2f_occupancy_preserving_relock_v1"
FAILED_ARCHIVE="/Users/subhojithalder/Desktop/Research Papers/Hole Aware XXZ Screening/deliverables/stage5c2gR3/HAXS_Stage5C2G_R3_1_G1_FAILED_EVIDENCE_20260728.zip"
FAILED_SHA="301dd288e536350ce47b8f919a6fe7b8fcd4fe609c5532a1646081121622e5dc"

cd "$ROOT"

# Phase 0: static/test evidence. Stop on any nonzero status.
python -m compileall -q src scripts scripts_patch tests
python scripts/run_tests.py
PYTHONPATH=src python -m pytest tests/stage5c2gR32 tests/stage5c2gR3 tests/regression -q

# Phase 1: S01. This creates immutable reconstruction evidence once.
python scripts/verify_failed_g1_evidence.py \
  --archive "$FAILED_ARCHIVE" \
  --expected-sha256 "$FAILED_SHA" \
  --out results/stage5c2gR32/S01

# Phase 2: S02. Pre-candidate scientific development only.
python scripts/run_stage5c2gR32_phase_quadrature.py \
  --config configs/stage5c2gR32/g1_phase_quadrature.yaml \
  --out output/stage5c2gR32/g1_preflight

# Phase 3: S03. This is the longer CPU calibration.
python scripts/calibrate_stage5c2gR32_statistical_sanity.py \
  --config configs/stage5c2gR32/sanity_calibration.yaml \
  --out output/stage5c2gR32/sanity_calibration

# Phase 4: wheel and candidate. Only after S01-S03 report PASS.
mkdir -p output/stage5c2gR32
python -m pip wheel . --no-deps --no-build-isolation \
  --wheel-dir output/stage5c2gR32
python scripts/build_stage5c2gR32_candidate.py
python scripts/package_stage5c2gR32_protocol.py

# Phase 5A: local physical host G0.
python scripts/run_stage5c2gR32_g0.py \
  --host-tag HOST_A \
  --protocol-archive output/stage5c2gR32/HAXS_Stage5C2G_R3_2_Protocol.zip \
  --out results/stage5c2gR32/g0/HOST_A

# Phase 5B runs from a fresh extraction on a physically distinct host.
# Compare returned attestations only after both hosts report PASS.
python scripts/compare_stage5c2gR32_g0_hosts.py \
  --host-a results/stage5c2gR32/g0/HOST_A/HOST_ATTESTATION.json \
  --host-b results/stage5c2gR32/g0/HOST_B/HOST_ATTESTATION.json \
  --out results/stage5c2gR32/g0/TWO_HOST_G0.json

# Phase 6: supervisor-review return. This may be large because S03 raw data is retained.
python scripts/package_stage5c2gR32_supervisor_review.py \
  --host-a results/stage5c2gR32/g0/HOST_A/HOST_ATTESTATION.json \
  --host-b results/stage5c2gR32/g0/HOST_B/HOST_ATTESTATION.json \
  --two-host-comparison results/stage5c2gR32/g0/TWO_HOST_G0.json

echo "STOP_BEFORE_OFFICIAL_G1_AND_RETURN_FOR_SUPERVISORY_REVIEW"
