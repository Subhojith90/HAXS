#!/usr/bin/env bash
set -euo pipefail

REPOSITORY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
: "${HAXS_RUN_ROOT:?HAXS_RUN_ROOT must be defined by the workflow}"
export HAXS_HOST_LABEL="HOST_B"

bash "$REPOSITORY_ROOT/ci/run_stage5c2gR32A5_g0.sh"

HOST_B_ROOT="$HAXS_RUN_ROOT/g0/evidence"
HOST_A_ROOT="$REPOSITORY_ROOT/ci/frozen/stage5c2gR32A5/reference/HOST_A"
PROTOCOL="$REPOSITORY_ROOT/releases/stage5c2gR32A5/HAXS_Stage5C2G_R3_2A_5_Protocol.zip"
PROTOCOL_SIDECAR="$REPOSITORY_ROOT/releases/stage5c2gR32A5/HAXS_Stage5C2G_R3_2A_5_Protocol_SHA256.txt"
DELIVERABLES="$HAXS_RUN_ROOT/deliverables"
PY="$HAXS_RUN_ROOT/venv/bin/python"

if [[ ! -f "$PROTOCOL" ]]; then
  PROTOCOL="$HAXS_RUN_ROOT/transport/HAXS_Stage5C2G_R3_2A_5_Protocol.zip"
fi

[[ -f "$PROTOCOL" && -f "$PROTOCOL_SIDECAR" ]]
EXPECTED_PROTOCOL_SHA256="$(awk 'NF {print $1; exit}' "$PROTOCOL_SIDECAR")"
ACTUAL_PROTOCOL_SHA256="$(shasum -a 256 "$PROTOCOL" | awk '{print $1}')"
[[ "$EXPECTED_PROTOCOL_SHA256" == "$ACTUAL_PROTOCOL_SHA256" ]]
echo "SUPERVISOR_RETURN_PROTOCOL_IDENTITY=PASS sha256=$ACTUAL_PROTOCOL_SHA256"

"$PY" -I "$REPOSITORY_ROOT/scripts/package_stage5c2gR32A5_supervisor_return.py" \
  --host-a-root "$HOST_A_ROOT" --host-b-root "$HOST_B_ROOT" \
  --protocol "$PROTOCOL" --out-dir "$DELIVERABLES"

cd "$DELIVERABLES"
shasum -a 256 -c HAXS_Stage5C2G_R3_2A_5_Complete_G0_Return_SHA256.txt
echo "R32A5_GITHUB_HOST_B_COMPLETE_RETURN=PASS"
