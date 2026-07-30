#!/usr/bin/env bash
set -euo pipefail

# Stage 5C.2G-R3.1 G0 only. Run HOST_A and HOST_B blocks on two physically
# distinct Apple-silicon Macs. Never run the G1 launcher before a new candidate
# is accepted and an exact structured JSON receipt is finalized.

# On each host, from a fresh extraction of the same source package:
# python3.12 -m venv /tmp/haxs-stage5c2gr3-1-host-a
# . /tmp/haxs-stage5c2gr3-1-host-a/bin/activate
# python -m pip install --only-binary=:all: --require-hashes -r requirements-stage5c2gR3.lock
# unset PYTHONPATH PYTHONHOME PYTHONSTARTUP PYTHONINSPECT PYTHONUSERBASE LD_PRELOAD DYLD_INSERT_LIBRARIES DYLD_LIBRARY_PATH
# export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1
# export HAXS_CUSTODY_ROOT=/READ_ONLY/EXTERNAL/CUSTODY
# mkdir -p results/stage5c2gR3/transcripts/authoritative/HOST_A
# { python -m compileall -q src scripts tests && echo "COMPILEALL_STATUS=PASS"; } 2>&1 | tee results/stage5c2gR3/transcripts/authoritative/HOST_A/00_compileall.txt
# python -I scripts/check_stage5c2gR3_static_gate.py 2>&1 | tee results/stage5c2gR3/transcripts/authoritative/HOST_A/01_static_gate.txt
# python scripts/run_tests.py 2>&1 | tee results/stage5c2gR3/transcripts/authoritative/HOST_A/02_full_tests.txt
# python -m pytest tests/stage5c2gR3 tests/regression -q 2>&1 | tee results/stage5c2gR3/transcripts/authoritative/HOST_A/03_targeted_tests.txt
# python -I scripts/verify_stage5c2gR3_immutable_install.py 2>&1 | tee results/stage5c2gR3/transcripts/authoritative/HOST_A/04_immutable_install.txt
# python -I scripts/verify_stage5c2gR3_protocol.py --custody-root "$HAXS_CUSTODY_ROOT" 2>&1 | tee results/stage5c2gR3/transcripts/authoritative/HOST_A/05_candidate.txt
# python -I scripts/package_stage5c2gR3_protocol.py 2>&1 | tee results/stage5c2gR3/transcripts/authoritative/HOST_A/06_package.txt
# python -I scripts/verify_stage5c2gR3_fresh_unzip.py --submission output/stage5c2gR3/HAXS_Stage5C2G_R3_1_Protocol.zip --custody-root "$HAXS_CUSTODY_ROOT" 2>&1 | tee results/stage5c2gR3/transcripts/authoritative/HOST_A/07_fresh_unzip.txt
# python -I scripts/write_stage5c2gR3_1_host_attestation.py --host-label HOST_A --transcript-dir results/stage5c2gR3/transcripts/authoritative/HOST_A --out results/stage5c2gR3/host_attestations/HOST_A.json 2>&1 | tee results/stage5c2gR3/transcripts/authoritative/HOST_A/08_host_attestation.txt

# Repeat on the second physical Mac with HOST_B in the virtual-environment,
# transcript-directory, --host-label, and attestation names. Bring only the
# HOST_B authoritative directory and HOST_B.json back to HOST_A.

# Final two-host check and supervisor-review package, on HOST_A:
# python -I scripts/verify_stage5c2gR3_1_two_physical_hosts.py --host-a results/stage5c2gR3/host_attestations/HOST_A.json --host-b results/stage5c2gR3/host_attestations/HOST_B.json
# python -I scripts/package_stage5c2gR3_1_supervisor_review.py --host-a-attestation results/stage5c2gR3/host_attestations/HOST_A.json --host-b-attestation results/stage5c2gR3/host_attestations/HOST_B.json --host-a-transcripts results/stage5c2gR3/transcripts/authoritative/HOST_A --host-b-transcripts results/stage5c2gR3/transcripts/authoritative/HOST_B

# STOP. Send the supervisor-review ZIP and its SHA-256 sidecar. Do not create a
# receipt yourself, finalize the candidate, or run G1.
