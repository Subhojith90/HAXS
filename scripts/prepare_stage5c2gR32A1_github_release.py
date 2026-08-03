#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))
from stage5c2gR32A1_authorization import ROOT, sha256_file

STAGE = "stage5c2gR32A1"
ARCHIVE_NAME = "HAXS_Stage5C2G_R3_2A_1_Protocol.zip"
SIDECAR_NAME = "HAXS_Stage5C2G_R3_2A_1_Protocol_SHA256.txt"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--host-a-run",
        type=Path,
        required=True,
        help="Fresh Host-A run root produced by ci/run_stage5c2gR32A1_host_a_g0.sh",
    )
    args = parser.parse_args()
    source_output = ROOT / "output" / STAGE
    release = ROOT / "releases" / STAGE
    reference = ROOT / "ci/frozen" / STAGE / "reference"
    manifest_path = ROOT / "ci/frozen" / STAGE / "INPUT_MANIFEST_SHA256.txt"
    targets = [
        release / ARCHIVE_NAME,
        release / SIDECAR_NAME,
        release / "RELEASE.json",
        reference / "HOST_A.json",
        reference / "HOST_A_transcripts",
        reference / "HOST_A_junit",
        manifest_path,
    ]
    if any(path.exists() or path.is_symlink() for path in targets):
        raise RuntimeError("refusing to overwrite frozen R3.2A.1 release inputs")

    host_run = args.host_a_run.resolve()
    sources = {
        release / ARCHIVE_NAME: source_output / ARCHIVE_NAME,
        release / SIDECAR_NAME: source_output / SIDECAR_NAME,
        reference / "HOST_A.json": host_run / "evidence/HOST_A.json",
    }
    if any(not path.is_file() or path.is_symlink() for path in sources.values()):
        raise RuntimeError("protocol or Host-A source evidence is missing or unsafe")
    release.mkdir(parents=True, exist_ok=True)
    reference.mkdir(parents=True, exist_ok=True)
    for target, source in sources.items():
        shutil.copyfile(source, target)
    shutil.copytree(
        host_run / "evidence/HOST_A_transcripts",
        reference / "HOST_A_transcripts",
    )
    shutil.copytree(
        host_run / "evidence/HOST_A_junit",
        reference / "HOST_A_junit",
    )

    release_metadata = {
        "schema_version": "haxs.stage5c2gR32A1.release.v1",
        "stage": "Stage5C2G-R3.2A.1",
        "candidate_sha256": json.loads(
            (
                ROOT / "results/stage5c2gR32A1/protocol/CANDIDATE.json"
            ).read_text(encoding="utf-8")
        )["candidate_sha256"],
        "protocol_archive_sha256": sha256_file(release / ARCHIVE_NAME),
        "host_a_sha256": sha256_file(reference / "HOST_A.json"),
        "host_b_status": "PENDING",
        "G1_authorized": False,
        "scientific_execution_performed": False,
    }
    (release / "RELEASE.json").write_text(
        json.dumps(release_metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    frozen = ROOT / "ci/frozen" / STAGE
    toolchain = ROOT / "ci/frozen/stage5c2gR32A"
    inputs = [
        ROOT / ".github/workflows/stage5c2gR32A1-host-b-g0.yml",
        ROOT / "ci/run_stage5c2gR32A1_g0.sh",
        ROOT / "ci/run_stage5c2gR32A1_github_host_b_g0.sh",
        *[
            path
            for base in [
                toolchain / "runtime",
                toolchain / "wheelhouse",
                reference,
            ]
            for path in base.rglob("*")
            if path.is_file() and not path.is_symlink()
        ],
        release / ARCHIVE_NAME,
        release / SIDECAR_NAME,
        release / "RELEASE.json",
    ]
    relative_inputs = sorted(
        {path.relative_to(ROOT).as_posix(): path for path in inputs}.items()
    )
    manifest_path.write_text(
        "".join(
            f"{sha256_file(path)}  {relative}\n"
            for relative, path in relative_inputs
        ),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "PASS",
                "input_manifest_files": len(relative_inputs),
                **release_metadata,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
