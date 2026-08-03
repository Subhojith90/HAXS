#!/usr/bin/env bash
set -euo pipefail

EXPECTED_ANACONDA_SHA256="f64ed797ce23ae1d07ead949bfb6ff630b9fa8269ca8aef8ea2efa82172ece47"
EXPECTED_PYTHON_SHA256="475b4a6cffa067fcef02b4b5ee7692857661282c1f34392f3dde7bc311472689"
ANACONDA_URL="https://repo.anaconda.com/archive/Anaconda3-2024.10-1-MacOSX-arm64.sh"

REPOSITORY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLCHAIN="$REPOSITORY_ROOT/ci/frozen/stage5c2gR32A"
RELEASE="$REPOSITORY_ROOT/releases/stage5c2gR32A1"
RUN="${HAXS_RUN_ROOT:?HAXS_RUN_ROOT must be defined}"
HOST_LABEL="${HAXS_HOST_LABEL:?HAXS_HOST_LABEL must be HOST_A or HOST_B}"
if [[ "$HOST_LABEL" != "HOST_A" && "$HOST_LABEL" != "HOST_B" ]]; then
  echo "HOST_LABEL_STATUS=FAIL value=$HOST_LABEL"
  exit 1
fi

PROTOCOL="${HAXS_PROTOCOL_ARCHIVE:-$RELEASE/HAXS_Stage5C2G_R3_2A_1_Protocol.zip}"
SIDECAR="${HAXS_PROTOCOL_SIDECAR:-$RELEASE/HAXS_Stage5C2G_R3_2A_1_Protocol_SHA256.txt}"
PROTOCOL_PARENT="$RUN/protocol"
ROOT="$PROTOCOL_PARENT/HAXS_Stage5C2G_R3_2A_1_Protocol"
DIAGNOSTICS="$RUN/diagnostics"
EVIDENCE="$RUN/evidence"
VENV="$RUN/venv"
ANACONDA="$RUN/anaconda3"
INSTALLER="$RUN/Anaconda3-2024.10-1-MacOSX-arm64.sh"
BOUND_PYTHON="$TOOLCHAIN/runtime/python3.12"
VENV_PY="$VENV/bin/python"

if [[ -e "$RUN" ]]; then
  echo "G0_STOP_EXISTING_RUN_ROOT=$RUN"
  exit 1
fi
mkdir -p "$DIAGNOSTICS" "$EVIDENCE" "$PROTOCOL_PARENT"
exec > >(tee "$DIAGNOSTICS/${HOST_LABEL}_WORKFLOW_ORCHESTRATION.txt") 2>&1

echo "HAXS Stage 5C.2G-R3.2A.1 $HOST_LABEL G0"
echo "Scope: G0 only. G1-G4 and all scientific execution are forbidden."
test "$(uname -s)" = "Darwin"
test "$(uname -m)" = "arm64"
test -f "$PROTOCOL"
test -f "$SIDECAR"
EXPECTED_PROTOCOL_SHA256="$(awk 'NF {print $1; exit}' "$SIDECAR")"
ACTUAL_PROTOCOL_SHA256="$(shasum -a 256 "$PROTOCOL" | awk '{print $1}')"
test -n "$EXPECTED_PROTOCOL_SHA256"
test "$EXPECTED_PROTOCOL_SHA256" = "$ACTUAL_PROTOCOL_SHA256"
echo "PROTOCOL_ARCHIVE_IDENTITY=PASS sha256=$ACTUAL_PROTOCOL_SHA256"

if [[ -n "${HAXS_ANACONDA_INSTALLER_SOURCE:-}" ]]; then
  test -f "$HAXS_ANACONDA_INSTALLER_SOURCE"
  cp "$HAXS_ANACONDA_INSTALLER_SOURCE" "$INSTALLER"
  echo "ANACONDA_INSTALLER_SOURCE=HASH_VERIFIED_LOCAL_COPY"
else
  curl --fail --location --retry 3 --retry-all-errors \
    "$ANACONDA_URL" --output "$INSTALLER"
fi
echo "$EXPECTED_ANACONDA_SHA256  $INSTALLER" | shasum -a 256 -c -
bash "$INSTALLER" -b -p "$ANACONDA"

unzip -q "$PROTOCOL" -d "$PROTOCOL_PARENT"
test -f "$ROOT/BUNDLE_CONTENTS_SHA256.txt"

"$ANACONDA/bin/python3.12" -m venv "$VENV"
rm -f "$VENV/bin/python" "$VENV/bin/python3" "$VENV/bin/python3.12"
ln -s "$BOUND_PYTHON" "$VENV/bin/python"
ln -s "$BOUND_PYTHON" "$VENV/bin/python3"
ln -s "$BOUND_PYTHON" "$VENV/bin/python3.12"
echo "$EXPECTED_PYTHON_SHA256  $BOUND_PYTHON" | shasum -a 256 -c -
echo "$EXPECTED_PYTHON_SHA256  $VENV_PY" | shasum -a 256 -c -

unset PYTHONPATH PYTHONHOME PYTHONSTARTUP PYTHONINSPECT PYTHONUSERBASE
unset LD_PRELOAD DYLD_INSERT_LIBRARIES DYLD_LIBRARY_PATH HAXS_CUSTODY_ROOT
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPYCACHEPREFIX="$EVIDENCE/${HOST_LABEL}_bootstrap_pycache"
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1
export NUMEXPR_NUM_THREADS=1

"$VENV_PY" -I -m pip install \
  --no-index \
  --find-links "$TOOLCHAIN/wheelhouse" \
  --only-binary=:all: \
  --require-hashes \
  -r "$ROOT/requirements-stage5c2gR3.lock"
"$VENV_PY" -I -m pip install \
  --no-index \
  --no-deps \
  "$TOOLCHAIN/wheelhouse/pip-26.1.2-py3-none-any.whl"
"$VENV_PY" -I -m pip install \
  --no-index \
  --no-deps \
  "$ROOT/output/stage5c2gR32A1/haxs-0.8.4-py3-none-any.whl"

cd "$ROOT"
"$VENV_PY" -I -B scripts/run_stage5c2gR32A1_g0.py \
  --host-label "$HOST_LABEL" \
  --protocol "$PROTOCOL" \
  --out "$EVIDENCE/$HOST_LABEL.json" \
  2>&1 | tee "$DIAGNOSTICS/${HOST_LABEL}_G0.txt"

echo "${HOST_LABEL}_G0_STATUS=PASS"
echo "EVIDENCE_PATH=$EVIDENCE"
echo "STOP_NO_G1"
