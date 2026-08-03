# Stage 5C.2G-R3.2A.1 runbook

## Scope

This stage repairs only the candidate-bound receipt/finalizer/launcher
interface and the self-contained execution root. It does not authorize or run
G1. G2-G4 and every downstream scope remain blocked.

All commands must run from the canonical `HAXS` repository on branch
`work/stage5c2g-r32a1`. Never delete, overwrite, extend, or select among
failed outputs.

## Phase 0 - exact local build environment

Use the manifest-bound CPython 3.12.7 executable and offline wheelhouse:

```bash
cd "/Users/subhojithalder/Desktop/Research Papers/Hole Aware XXZ Screening/HAXS"

BUILD_ROOT="$(mktemp -d /tmp/haxs-stage5c2gr32a1-build.XXXXXX)"
PY="$BUILD_ROOT/venv/bin/python"
FROZEN="$PWD/ci/frozen/stage5c2gR32A"

"$FROZEN/runtime/python3.12" -m venv "$BUILD_ROOT/venv"
rm -f "$BUILD_ROOT/venv/bin/python" \
      "$BUILD_ROOT/venv/bin/python3" \
      "$BUILD_ROOT/venv/bin/python3.12"
ln -s "$FROZEN/runtime/python3.12" "$BUILD_ROOT/venv/bin/python"
ln -s "$FROZEN/runtime/python3.12" "$BUILD_ROOT/venv/bin/python3"
ln -s "$FROZEN/runtime/python3.12" "$BUILD_ROOT/venv/bin/python3.12"

"$PY" -I -m pip install \
  --no-index \
  --find-links "$FROZEN/wheelhouse" \
  --only-binary=:all: \
  --require-hashes \
  -r requirements-stage5c2gR3.lock

"$PY" -I -m pip install \
  --no-index --no-deps \
  "$FROZEN/wheelhouse/pip-26.1.2-py3-none-any.whl"

export R32A1_BUILD_ROOT="$BUILD_ROOT"
export R32A1_PY="$PY"
```

Keep the same terminal open for the remaining local phases.

## Phase 1 - wheel, environment, ledgers, and tests

```bash
cd "/Users/subhojithalder/Desktop/Research Papers/Hole Aware XXZ Screening/HAXS"
PY="$R32A1_PY"

mkdir -p \
  output/stage5c2gR32A1 \
  results/stage5c2gR32A1/protocol \
  results/stage5c2gR32A1/junit \
  results/stage5c2gR32A1/transcripts

WHEEL_SOURCE="$R32A1_BUILD_ROOT/wheel-source"
test ! -e "$WHEEL_SOURCE"
mkdir -p "$WHEEL_SOURCE/src"
cp pyproject.toml "$WHEEL_SOURCE/"
cp -R src/haxs "$WHEEL_SOURCE/src/"

"$PY" -I -m pip wheel \
  --no-index \
  --no-deps \
  --no-build-isolation \
  --wheel-dir output/stage5c2gR32A1 \
  "$WHEEL_SOURCE" \
  2>&1 | tee results/stage5c2gR32A1/transcripts/wheel_build.txt

"$PY" -I scripts/write_stage5c2gR32A1_environment.py \
  2>&1 | tee results/stage5c2gR32A1/transcripts/00_environment.txt

"$PY" -I scripts/write_stage5c2gR32A1_test_ledger.py \
  2>&1 | tee results/stage5c2gR32A1/transcripts/01_test_ledger.txt

"$PY" -I scripts/write_stage5c2gR32A1_root_manifest.py \
  2>&1 | tee results/stage5c2gR32A1/transcripts/02_root_manifest.txt

"$PY" -m compileall -q src scripts scripts_patch tests \
  2>&1 | tee results/stage5c2gR32A1/transcripts/03_compileall.txt

"$PY" -m pytest -q -p no:cacheprovider \
  --junitxml=results/stage5c2gR32A1/junit/full_tests.xml \
  2>&1 | tee results/stage5c2gR32A1/transcripts/04_full_tests.txt

"$PY" -m pytest -q -p no:cacheprovider \
  tests/stage5c2gR32A1 tests/stage5c2gR32A tests/regression \
  --junitxml=results/stage5c2gR32A1/junit/targeted_tests.xml \
  2>&1 | tee results/stage5c2gR32A1/transcripts/05_targeted_tests.txt

"$PY" -I scripts/verify_stage5c2gR32A1_immutable_install.py \
  2>&1 | tee results/stage5c2gR32A1/transcripts/06_immutable_install.txt
```

Stop and return the complete output if any command fails. Do not rebuild or
overwrite any generated ledger.

## Phase 2 - candidate, protocol, and strict fresh-unzip gate

Run only after every Phase 1 command passes:

```bash
"$PY" -I scripts/build_stage5c2gR32A1_candidate.py \
  --fail-closed \
  2>&1 | tee results/stage5c2gR32A1/transcripts/07_candidate.txt

"$PY" -I scripts/package_stage5c2gR32A1_protocol.py \
  2>&1 | tee results/stage5c2gR32A1/transcripts/08_package.txt

"$PY" -I scripts/verify_stage5c2gR32A1_fresh_unzip.py \
  --protocol output/stage5c2gR32A1/HAXS_Stage5C2G_R3_2A_1_Protocol.zip \
  --strict-root \
  --junit results/stage5c2gR32A1/junit/fresh_unzip.xml \
  2>&1 | tee results/stage5c2gR32A1/transcripts/09_fresh_unzip.txt
```

Stop before Host-A G0 and return all Phase 1-2 output for review.

## Phase 3 - replacement Host-A G0

Run only after Phase 2 review:

```bash
export HAXS_RUN_ROOT="/tmp/haxs-stage5c2gr32a1-host-a.$(uuidgen | tr -d '-')"
test ! -e "$HAXS_RUN_ROOT"
bash ci/run_stage5c2gR32A1_host_a_g0.sh
```

The run root must not exist before launch. Preserve the printed path.

After Host A passes:

```bash
"$R32A1_PY" -I scripts/prepare_stage5c2gR32A1_github_release.py \
  --host-a-run "$HAXS_RUN_ROOT"
```

Commit the generated release/reference files on the work branch. Create the
immutable release branch only after local review.

## Phase 4 - GitHub Host-B G0

Dispatch `.github/workflows/stage5c2gR32A1-host-b-g0.yml` from the exact
release branch and commit. Download its artifact and stop.

No receipt may be created and no G1 command may be invoked during this
runbook.
