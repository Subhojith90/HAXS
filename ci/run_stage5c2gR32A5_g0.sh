#!/usr/bin/env bash
set -euo pipefail

EXPECTED_ANACONDA_SHA256="f64ed797ce23ae1d07ead949bfb6ff630b9fa8269ca8aef8ea2efa82172ece47"
ANACONDA_URL="https://repo.anaconda.com/archive/Anaconda3-2024.10-1-MacOSX-arm64.sh"
REPOSITORY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RELEASE="$REPOSITORY_ROOT/releases/stage5c2gR32A5"
RUN="${HAXS_RUN_ROOT:?HAXS_RUN_ROOT must be defined}"
HOST_LABEL="${HAXS_HOST_LABEL:?HAXS_HOST_LABEL must be HOST_A or HOST_B}"
[[ "$HOST_LABEL" == "HOST_A" || "$HOST_LABEL" == "HOST_B" ]]

PROTOCOL="${HAXS_PROTOCOL_ARCHIVE:-$RELEASE/HAXS_Stage5C2G_R3_2A_5_Protocol.zip}"
SIDECAR="${HAXS_PROTOCOL_SIDECAR:-$RELEASE/HAXS_Stage5C2G_R3_2A_5_Protocol_SHA256.txt}"
PROTOCOL_PARENT="$RUN/protocol"
EXTRACTED="$PROTOCOL_PARENT/HAXS_Stage5C2G_R3_2A_5_Protocol"
DIAGNOSTICS="$RUN/diagnostics"
ANACONDA="$RUN/anaconda3"
INSTALLER="$RUN/Anaconda3-2024.10-1-MacOSX-arm64.sh"
VENV="$RUN/venv"
BOUND_PYTHON="$EXTRACTED/ci/frozen/stage5c2gR32A/runtime/python3.12"
PY="$VENV/bin/python"

[[ ! -e "$RUN" ]]
mkdir -p "$DIAGNOSTICS" "$PROTOCOL_PARENT" "$RUN/transport"
exec > >(tee "$DIAGNOSTICS/${HOST_LABEL}_WORKFLOW_ORCHESTRATION.txt") 2>&1
[[ "$(uname -s)" == "Darwin" && "$(uname -m)" == "arm64" ]]

if [[ ! -f "$PROTOCOL" ]]; then
  CHUNK_MANIFEST="$RELEASE/HAXS_Stage5C2G_R3_2A_5_Protocol_CHUNKS_SHA256.txt"
  CHUNK_DIR="$RELEASE/HAXS_Stage5C2G_R3_2A_5_Protocol.chunks"
  [[ -f "$CHUNK_MANIFEST" && -d "$CHUNK_DIR" ]]
  (cd "$RELEASE" && shasum -a 256 -c "$(basename "$CHUNK_MANIFEST")")
  shopt -s nullglob
  CHUNKS=("$CHUNK_DIR"/HAXS_Stage5C2G_R3_2A_5_Protocol.zip.part-*)
  shopt -u nullglob
  [[ "${#CHUNKS[@]}" -ge 2 ]]
  PROTOCOL="$RUN/transport/HAXS_Stage5C2G_R3_2A_5_Protocol.zip"
  cat "${CHUNKS[@]}" > "$PROTOCOL"
fi

EXPECTED_PROTOCOL="$(awk 'NF {print $1; exit}' "$SIDECAR")"
ACTUAL_PROTOCOL="$(shasum -a 256 "$PROTOCOL" | awk '{print $1}')"
[[ "$EXPECTED_PROTOCOL" == "$ACTUAL_PROTOCOL" ]]
unzip -q "$PROTOCOL" -d "$PROTOCOL_PARENT"

[[ -f "$BOUND_PYTHON" && ! -L "$BOUND_PYTHON" ]]
chmod 0555 "$BOUND_PYTHON"
[[ -x "$BOUND_PYTHON" ]]
echo "BOUND_PYTHON_EXECUTABLE_MODE=PASS"

curl --fail --location --retry 3 --retry-all-errors "$ANACONDA_URL" --output "$INSTALLER"
echo "$EXPECTED_ANACONDA_SHA256  $INSTALLER" | shasum -a 256 -c -
bash "$INSTALLER" -b -p "$ANACONDA"
"$ANACONDA/bin/python3.12" -m venv "$VENV"
rm -f "$VENV/bin/python" "$VENV/bin/python3" "$VENV/bin/python3.12"
ln -s "$BOUND_PYTHON" "$VENV/bin/python"
ln -s "$BOUND_PYTHON" "$VENV/bin/python3"
ln -s "$BOUND_PYTHON" "$VENV/bin/python3.12"

unset PYTHONPATH PYTHONHOME PYTHONSTARTUP PYTHONINSPECT PYTHONUSERBASE
unset LD_PRELOAD DYLD_INSERT_LIBRARIES DYLD_LIBRARY_PATH
export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1

"$PY" -I -m pip install --no-index \
  --find-links "$EXTRACTED/ci/frozen/stage5c2gR32A/wheelhouse" \
  --only-binary=:all: --require-hashes \
  -r "$EXTRACTED/requirements-stage5c2gR3.lock"
"$PY" -I -m pip install --no-index --no-deps \
  "$EXTRACTED/ci/frozen/stage5c2gR32A/wheelhouse/pip-26.1.2-py3-none-any.whl"
"$PY" -I -m pip install --no-index --no-deps \
  "$EXTRACTED/output/stage5c2gR32A5/haxs-0.8.8-py3-none-any.whl"

cd "$EXTRACTED"
HAXS_R32A5_PYTHON="$PY" HAXS_RUN_ROOT="$RUN/g0" \
  HAXS_PROTOCOL_ARCHIVE="$PROTOCOL" HAXS_PROTOCOL_SIDECAR="$SIDECAR" \
  bash run_stage5c2gR32A5_G0.sh --host-label "$HOST_LABEL"

echo "${HOST_LABEL}_G0_STATUS=PASS"
echo "STOP_NO_RECEIPT_NO_G1"
