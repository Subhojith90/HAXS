#!/usr/bin/env bash
set -euo pipefail

export HAXS_HOST_LABEL="HOST_A"
: "${HAXS_RUN_ROOT:?Set HAXS_RUN_ROOT to a new, nonexistent directory}"

REPOSITORY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export HAXS_PROTOCOL_ARCHIVE="$REPOSITORY_ROOT/output/stage5c2gR32A1/HAXS_Stage5C2G_R3_2A_1_Protocol.zip"
export HAXS_PROTOCOL_SIDECAR="$REPOSITORY_ROOT/output/stage5c2gR32A1/HAXS_Stage5C2G_R3_2A_1_Protocol_SHA256.txt"
exec bash "$REPOSITORY_ROOT/ci/run_stage5c2gR32A1_g0.sh"
