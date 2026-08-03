#!/usr/bin/env bash
set -euo pipefail

REPOSITORY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export HAXS_HOST_LABEL="HOST_B"
: "${HAXS_RUN_ROOT:?HAXS_RUN_ROOT must be defined}"

bash "$REPOSITORY_ROOT/ci/run_stage5c2gR32A1_g0.sh"

RUN="$HAXS_RUN_ROOT"
FROZEN="$REPOSITORY_ROOT/ci/frozen/stage5c2gR32A1"
RELEASE="$REPOSITORY_ROOT/releases/stage5c2gR32A1"
ROOT="$RUN/protocol/HAXS_Stage5C2G_R3_2A_1_Protocol"
EVIDENCE="$RUN/evidence"
DELIVERABLES="$RUN/deliverables"
mkdir -p "$DELIVERABLES"

"$RUN/venv/bin/python" -I \
  "$ROOT/scripts/compare_stage5c2gR32A1_g0_hosts.py" \
  --host-a "$FROZEN/reference/HOST_A.json" \
  --host-b "$EVIDENCE/HOST_B.json" \
  --out "$EVIDENCE/TWO_HOST_G0.json" \
  2>&1 | tee "$RUN/diagnostics/TWO_HOST_COMPARISON.txt"

RETURN_ROOT="$RUN/HAXS_Stage5C2G_R3_2A_1_G0_RETURN"
mkdir -p \
  "$RETURN_ROOT/protocol" \
  "$RETURN_ROOT/candidate" \
  "$RETURN_ROOT/g0/HOST_A_transcripts" \
  "$RETURN_ROOT/g0/HOST_A_junit" \
  "$RETURN_ROOT/g0/HOST_B_transcripts" \
  "$RETURN_ROOT/g0/HOST_B_junit"
cp "$RELEASE/HAXS_Stage5C2G_R3_2A_1_Protocol.zip" \
  "$RELEASE/HAXS_Stage5C2G_R3_2A_1_Protocol_SHA256.txt" \
  "$RETURN_ROOT/protocol/"
cp "$ROOT/results/stage5c2gR32A1/protocol/CANDIDATE.json" \
  "$ROOT/results/stage5c2gR32A1/protocol/NAMED_TEST_LEDGER.json" \
  "$ROOT/results/stage5c2gR32A1/protocol/ROOT_MANIFEST.json" \
  "$RETURN_ROOT/candidate/"
cp "$FROZEN/reference/HOST_A.json" \
  "$EVIDENCE/HOST_B.json" \
  "$EVIDENCE/TWO_HOST_G0.json" \
  "$RETURN_ROOT/g0/"
cp "$FROZEN/reference/HOST_A_transcripts/"* \
  "$RETURN_ROOT/g0/HOST_A_transcripts/"
cp "$FROZEN/reference/HOST_A_junit/"* \
  "$RETURN_ROOT/g0/HOST_A_junit/"
cp "$EVIDENCE/HOST_B_transcripts/"* \
  "$RETURN_ROOT/g0/HOST_B_transcripts/"
cp "$EVIDENCE/HOST_B_junit/"* \
  "$RETURN_ROOT/g0/HOST_B_junit/"

(
  cd "$RETURN_ROOT"
  find . -type f ! -name RETURN_CONTENTS_SHA256.txt -print0 |
    sort -z |
    xargs -0 shasum -a 256 > RETURN_CONTENTS_SHA256.txt
)
(
  cd "$RUN"
  COPYFILE_DISABLE=1 zip -X -q -r \
    "$DELIVERABLES/HAXS_Stage5C2G_R3_2A_1_G0_RETURN.zip" \
    "$(basename "$RETURN_ROOT")"
)
(
  cd "$DELIVERABLES"
  shasum -a 256 HAXS_Stage5C2G_R3_2A_1_G0_RETURN.zip \
    > HAXS_Stage5C2G_R3_2A_1_G0_RETURN_SHA256.txt
  shasum -a 256 -c HAXS_Stage5C2G_R3_2A_1_G0_RETURN_SHA256.txt
)
cat > "$DELIVERABLES/GITHUB_RUN_PROVENANCE.txt" <<EOF
repository=${GITHUB_REPOSITORY:-}
branch=${GITHUB_REF_NAME:-}
commit=${GITHUB_SHA:-}
run_id=${GITHUB_RUN_ID:-}
run_attempt=${GITHUB_RUN_ATTEMPT:-}
run_url=${GITHUB_SERVER_URL:-https://github.com}/${GITHUB_REPOSITORY:-}/actions/runs/${GITHUB_RUN_ID:-}
runner_name=${RUNNER_NAME:-}
runner_environment=${RUNNER_ENVIRONMENT:-}
scope=G0_ONLY_STOP_NO_G1
EOF
(
  cd "$DELIVERABLES"
  shasum -a 256 \
    HAXS_Stage5C2G_R3_2A_1_G0_RETURN.zip \
    HAXS_Stage5C2G_R3_2A_1_G0_RETURN_SHA256.txt \
    GITHUB_RUN_PROVENANCE.txt \
    > GITHUB_DELIVERABLES_SHA256.txt
  shasum -a 256 -c GITHUB_DELIVERABLES_SHA256.txt
)
echo "TWO_HOST_G0_STATUS=PASS"
echo "STOP_NO_RECEIPT_NO_G1"
