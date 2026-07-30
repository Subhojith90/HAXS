#!/usr/bin/env bash
set -euo pipefail

EXPECTED_ANACONDA_SHA256="f64ed797ce23ae1d07ead949bfb6ff630b9fa8269ca8aef8ea2efa82172ece47"
EXPECTED_PYTHON_SHA256="475b4a6cffa067fcef02b4b5ee7692857661282c1f34392f3dde7bc311472689"
EXPECTED_CANDIDATE="1950c01dfd46f4c381e2d333dbd2c3bce1969b65140689961662c287dd54c165"
EXPECTED_PROTOCOL="b60cbfa1f5296d2d7844f4324d21b0b6743f2d10b93f373be1484e3fe79ae694"
EXPECTED_HOST_A="0f51b28c4893ee2f5a0fdd6264f60e278fad497a15cf0e27903c3e7a7b6b9134"
ANACONDA_URL="https://repo.anaconda.com/archive/Anaconda3-2024.10-1-MacOSX-arm64.sh"

REPOSITORY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FROZEN="$REPOSITORY_ROOT/ci/frozen/stage5c2gR32A"
RELEASE="$REPOSITORY_ROOT/releases/stage5c2gR32A"
RUN="${HAXS_RUN_ROOT:?HAXS_RUN_ROOT must be defined}"
DIAGNOSTICS="$RUN/diagnostics"
EVIDENCE="$RUN/evidence"
DELIVERABLES="$RUN/deliverables"
PROTOCOL_PARENT="$RUN/protocol"
ROOT="$PROTOCOL_PARENT/HAXS_Stage5C2G_R3_2A_Protocol"
VENV="$RUN/venv"
ANACONDA="$RUN/anaconda3"
INSTALLER="$RUN/Anaconda3-2024.10-1-MacOSX-arm64.sh"
BOUND_PYTHON="$FROZEN/runtime/python3.12"
VENV_PY="$VENV/bin/python"

mkdir -p "$DIAGNOSTICS" "$EVIDENCE" "$DELIVERABLES" "$PROTOCOL_PARENT"
exec > >(tee "$DIAGNOSTICS/WORKFLOW_ORCHESTRATION.txt") 2>&1

echo "HAXS Stage 5C.2G-R3.2A GitHub Host-B G0"
echo "Scope: G0 only. G1-G4 and downstream execution are forbidden."

if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
  echo "HOST_PLATFORM_STATUS=FAIL expected Darwin arm64"
  exit 1
fi

echo "$EXPECTED_PROTOCOL  $RELEASE/HAXS_Stage5C2G_R3_2A_Protocol.zip" |
  shasum -a 256 -c -
echo "$EXPECTED_HOST_A  $FROZEN/reference/HOST_A.json" |
  shasum -a 256 -c -

curl --fail --location --retry 3 --retry-all-errors \
  "$ANACONDA_URL" --output "$INSTALLER"
echo "$EXPECTED_ANACONDA_SHA256  $INSTALLER" | shasum -a 256 -c -
bash "$INSTALLER" -b -p "$ANACONDA"

unzip -q "$RELEASE/HAXS_Stage5C2G_R3_2A_Protocol.zip" \
  -d "$PROTOCOL_PARENT"

# The protocol bundle's self-excluded ledger is packaging metadata, not an
# execution-root entry. Preserve it in diagnostics and reconstruct the frozen
# legacy root contracts required by the full historical test suite.
mv "$ROOT/BUNDLE_CONTENTS_SHA256.txt" \
  "$DIAGNOSTICS/PROTOCOL_BUNDLE_CONTENTS_SHA256.txt"
cp "$REPOSITORY_ROOT/STAGE3_COMMANDS.sh" \
  "$REPOSITORY_ROOT/STAGE3A_COMMANDS.sh" \
  "$REPOSITORY_ROOT/STAGE5C2GR3_COMMANDS.sh" \
  "$REPOSITORY_ROOT/STAGE5C2GR32_COMMANDS.sh" \
  "$REPOSITORY_ROOT/requirements-stage5c2gR2.lock" \
  "$ROOT/"

# The protocol cannot recursively contain itself. Restore the exact archive and
# sidecar only for the packaged fresh-unzip G0 check.
cp "$RELEASE/HAXS_Stage5C2G_R3_2A_Protocol.zip" \
  "$RELEASE/HAXS_Stage5C2G_R3_2A_Protocol_SHA256.txt" \
  "$ROOT/output/stage5c2gR32A/"

"$ANACONDA/bin/python3.12" -m venv "$VENV"
rm -f "$VENV/bin/python" "$VENV/bin/python3" "$VENV/bin/python3.12"
ln -s "$BOUND_PYTHON" "$VENV/bin/python"
ln -s "$BOUND_PYTHON" "$VENV/bin/python3"
ln -s "$BOUND_PYTHON" "$VENV/bin/python3.12"

echo "$EXPECTED_PYTHON_SHA256  $BOUND_PYTHON" | shasum -a 256 -c -
echo "$EXPECTED_PYTHON_SHA256  $VENV_PY" | shasum -a 256 -c -

unset PYTHONPATH PYTHONHOME PYTHONSTARTUP PYTHONINSPECT PYTHONUSERBASE
unset LD_PRELOAD DYLD_INSERT_LIBRARIES DYLD_LIBRARY_PATH
export HAXS_CUSTODY_ROOT="$FROZEN/custody"
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1
export NUMEXPR_NUM_THREADS=1

"$VENV_PY" -I -m pip install \
  --no-index \
  --find-links "$FROZEN/wheelhouse" \
  --only-binary=:all: \
  --require-hashes \
  -r "$ROOT/requirements-stage5c2gR3.lock"

# Host A records pip 26.1.2. Upgrade the installer tool from an independently
# manifest-bound wheel after the scientific lock is installed.
"$VENV_PY" -I -m pip install \
  --no-index \
  --no-deps \
  "$FROZEN/wheelhouse/pip-26.1.2-py3-none-any.whl"

"$VENV_PY" -I -m pip install \
  --no-index \
  --no-deps \
  "$ROOT/output/stage5c2gR32A/haxs-0.8.3-py3-none-any.whl"

"$VENV_PY" -I -c '
import importlib.metadata as metadata
import json
from pathlib import Path
import sys

expected = json.loads(Path(sys.argv[1]).read_text())["packages"]
actual = {name: metadata.version(name) for name in expected}
if actual != expected:
    raise SystemExit(f"environment package mismatch: expected={expected} actual={actual}")
print(json.dumps({"status": "PASS", "packages": actual}, sort_keys=True))
' "$ROOT/results/stage5c2gR32A/environment.json" |
  tee "$DIAGNOSTICS/ENVIRONMENT_PACKAGE_PREFLIGHT.json"

CANDIDATE_SHA="$("$VENV_PY" -I -c \
  'import json,sys; print(json.load(open(sys.argv[1]))["candidate_sha256"])' \
  "$ROOT/results/stage5c2gR32A/protocol/CANDIDATE.json")"
if [[ "$CANDIDATE_SHA" != "$EXPECTED_CANDIDATE" ]]; then
  echo "CANDIDATE_PREFLIGHT_STATUS=FAIL expected=$EXPECTED_CANDIDATE found=$CANDIDATE_SHA"
  exit 1
fi

"$VENV_PY" -I "$ROOT/scripts/run_stage5c2gR32A_g0.py" \
  --host-label HOST_B \
  --out "$EVIDENCE/HOST_B.json" \
  2>&1 | tee "$DIAGNOSTICS/HOST_B_G0.txt"

"$VENV_PY" -I "$ROOT/scripts/compare_stage5c2gR32A_g0_hosts.py" \
  --host-a "$FROZEN/reference/HOST_A.json" \
  --host-b "$EVIDENCE/HOST_B.json" \
  --out "$EVIDENCE/TWO_HOST_G0.json" \
  2>&1 | tee "$DIAGNOSTICS/TWO_HOST_COMPARISON.txt"

RETURN_ROOT="$RUN/HAXS_Stage5C2G_R3_2A_HOST_B_RETURN"
mkdir -p "$RETURN_ROOT/protocol" "$RETURN_ROOT/candidate" \
  "$RETURN_ROOT/g0/HOST_A_transcripts" "$RETURN_ROOT/g0/HOST_B_transcripts"
cp "$RELEASE/HAXS_Stage5C2G_R3_2A_Protocol.zip" \
  "$RELEASE/HAXS_Stage5C2G_R3_2A_Protocol_SHA256.txt" \
  "$RETURN_ROOT/protocol/"
cp "$ROOT/results/stage5c2gR32A/protocol/CANDIDATE.json" "$RETURN_ROOT/candidate/"
cp "$FROZEN/reference/HOST_A.json" "$RETURN_ROOT/g0/"
cp "$EVIDENCE/HOST_B.json" "$EVIDENCE/TWO_HOST_G0.json" "$RETURN_ROOT/g0/"
cp "$FROZEN/reference/HOST_A_transcripts/"*.txt \
  "$RETURN_ROOT/g0/HOST_A_transcripts/"
cp "$EVIDENCE/HOST_B_transcripts/"*.txt \
  "$RETURN_ROOT/g0/HOST_B_transcripts/"

(
  cd "$RETURN_ROOT"
  find . -type f ! -name RETURN_CONTENTS_SHA256.txt -print0 |
    sort -z |
    xargs -0 shasum -a 256 > RETURN_CONTENTS_SHA256.txt
)

(
  cd "$RUN"
  COPYFILE_DISABLE=1 zip -X -q -r \
    "$DELIVERABLES/HAXS_Stage5C2G_R3_2A_HOST_B_RETURN.zip" \
    "$(basename "$RETURN_ROOT")"
)

(
  cd "$DELIVERABLES"
  shasum -a 256 HAXS_Stage5C2G_R3_2A_HOST_B_RETURN.zip \
    > HAXS_Stage5C2G_R3_2A_HOST_B_RETURN_SHA256.txt
  shasum -a 256 -c HAXS_Stage5C2G_R3_2A_HOST_B_RETURN_SHA256.txt
)

cat > "$DELIVERABLES/GITHUB_RUN_PROVENANCE.txt" <<EOF
repository=${GITHUB_REPOSITORY:-}
release_branch=${GITHUB_REF_NAME:-}
commit=${GITHUB_SHA:-}
run_id=${GITHUB_RUN_ID:-}
run_attempt=${GITHUB_RUN_ATTEMPT:-}
run_url=${GITHUB_SERVER_URL:-https://github.com}/${GITHUB_REPOSITORY:-}/actions/runs/${GITHUB_RUN_ID:-}
runner_name=${RUNNER_NAME:-}
runner_environment=${RUNNER_ENVIRONMENT:-}
candidate_sha256=$EXPECTED_CANDIDATE
scope=G0_ONLY_STOP_NO_G1
EOF

(
  cd "$DELIVERABLES"
  shasum -a 256 \
    HAXS_Stage5C2G_R3_2A_HOST_B_RETURN.zip \
    HAXS_Stage5C2G_R3_2A_HOST_B_RETURN_SHA256.txt \
    GITHUB_RUN_PROVENANCE.txt \
    > GITHUB_DELIVERABLES_SHA256.txt
  shasum -a 256 -c GITHUB_DELIVERABLES_SHA256.txt
)

echo "HOST_B_COMPLETE_STATUS=PASS"
echo "TWO_HOST_G0_STATUS=PASS"
echo "RETURN_TO_SUBHOJIT=$DELIVERABLES"
echo "STOP_NO_G1"
