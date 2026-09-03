#!/usr/bin/env bash
set -euo pipefail

HOST_LABEL=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --host-label) HOST_LABEL="$2"; shift 2 ;;
    *) echo "Unknown argument: $1"; exit 2 ;;
  esac
done
[[ "$HOST_LABEL" == "HOST_A" || "$HOST_LABEL" == "HOST_B" ]]
: "${HAXS_RUN_ROOT:?HAXS_RUN_ROOT must point to a new external run directory}"
: "${HAXS_R32A3_PYTHON:?HAXS_R32A3_PYTHON must be exact isolated CPython 3.12.7}"

REPOSITORY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROTOCOL="${HAXS_PROTOCOL_ARCHIVE:-$REPOSITORY_ROOT/output/stage5c2gR32A3/HAXS_Stage5C2G_R3_2A_3_Protocol.zip}"
SIDECAR="${HAXS_PROTOCOL_SIDECAR:-$REPOSITORY_ROOT/output/stage5c2gR32A3/HAXS_Stage5C2G_R3_2A_3_Protocol_SHA256.txt}"
RUN="$HAXS_RUN_ROOT"
ROOT="$RUN/protocol/HAXS_Stage5C2G_R3_2A_3_Protocol"

[[ ! -e "$RUN" ]]
mkdir -p "$RUN/protocol" "$RUN/diagnostics"
exec > >(tee "$RUN/diagnostics/${HOST_LABEL}_ORCHESTRATION.txt") 2>&1

EXPECTED="$(awk 'NF {print $1; exit}' "$SIDECAR")"
ACTUAL="$(shasum -a 256 "$PROTOCOL" | awk '{print $1}')"
[[ "$EXPECTED" == "$ACTUAL" ]]
unzip -q "$PROTOCOL" -d "$RUN/protocol"
chmod -R a-w "$ROOT"

unset PYTHONPATH PYTHONHOME PYTHONSTARTUP PYTHONINSPECT PYTHONUSERBASE
unset LD_PRELOAD DYLD_INSERT_LIBRARIES DYLD_LIBRARY_PATH
export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1

cd "$ROOT"
"$HAXS_R32A3_PYTHON" -I -B scripts/run_stage5c2gR32A3_g0.py \
  --host-label "$HOST_LABEL" --protocol "$PROTOCOL" \
  --out "$RUN/evidence/$HOST_LABEL.json" \
  2>&1 | tee "$RUN/diagnostics/${HOST_LABEL}_G0.txt"

echo "${HOST_LABEL}_G0_STATUS=PASS"
echo "STOP_NO_RECEIPT_NO_G1"
