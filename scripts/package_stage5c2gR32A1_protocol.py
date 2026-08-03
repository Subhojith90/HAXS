#!/usr/bin/env python
from __future__ import annotations

import json
import stat
import sys
import zipfile
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))
from build_stage5c2gR32A1_candidate import closure_paths, runtime_paths
from stage5c2gR32A1_authorization import ROOT, sha256_file

PREFIX = "HAXS_Stage5C2G_R3_2A_1_Protocol"


def _info(name: str) -> zipfile.ZipInfo:
    item = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    item.external_attr = (stat.S_IFREG | 0o644) << 16
    return item


def main() -> None:
    output = ROOT / "output/stage5c2gR32A1"
    candidate = ROOT / "results/stage5c2gR32A1/protocol/CANDIDATE.json"
    wheel = output / "haxs-0.8.4-py3-none-any.whl"
    environment = ROOT / "results/stage5c2gR32A1/environment.json"
    generated_contracts = [
        ROOT / "results/stage5c2gR32A1/protocol/NAMED_TEST_LEDGER.json",
        ROOT / "results/stage5c2gR32A1/protocol/ROOT_MANIFEST.json",
    ]
    required = [candidate, wheel, environment, *generated_contracts]
    if any(not path.is_file() or path.is_symlink() for path in required):
        raise RuntimeError("candidate, wheel, environment, and generated contracts are required")

    sources: list[Path] = [
        *runtime_paths(),
        *closure_paths(),
        *required,
    ]
    for directory in [
        ROOT / "results/stage5c2gR32/S01",
        ROOT / "output/stage5c2gR32/g1_preflight",
        ROOT / "output/stage5c2gR32/sanity_calibration",
        ROOT / "output/stage5c2gR32A/g1_preflight",
        ROOT / "output/stage5c2gR32A/g1_preflight_failed_attempt_001",
        ROOT / "output/stage5c2gR32A/s03_development",
        ROOT / "output/stage5c2gR32A/s03_validation",
        ROOT / "results/stage5c2gR32A/transcripts",
        ROOT / "results/stage5c2gR32A1/development",
        ROOT / "results/stage5c2gR32A1/junit",
    ]:
        for path in sorted(directory.rglob("*")):
            if (
                path.is_file()
                and not path.is_symlink()
                and "__pycache__" not in path.parts
                and ".pytest_cache" not in path.parts
            ):
                sources.append(path)
    # Include only completed Phase-1 transcripts. The packaging command is
    # normally piped through tee to 08_package.txt; including that live file
    # would make the archive depend on write timing and would be self-referential.
    phase1_transcripts = ROOT / "results/stage5c2gR32A1/transcripts"
    for name in [
        "wheel_build.txt",
        "00_environment.txt",
        "01_test_ledger.txt",
        "02_root_manifest.txt",
        "03_compileall.txt",
        "04_full_tests.txt",
        "05_targeted_tests.txt",
        "06_immutable_install.txt",
        "07_candidate.txt",
    ]:
        path = phase1_transcripts / name
        if path.is_file() and not path.is_symlink():
            sources.append(path)
    unique = {
        path.relative_to(ROOT).as_posix(): path
        for path in sources
    }
    if any(
        Path(relative).is_absolute() or ".." in Path(relative).parts
        for relative in unique
    ):
        raise RuntimeError("package contains an unsafe path")

    archive = output / f"{PREFIX}.zip"
    sidecar = output / f"{PREFIX}_SHA256.txt"
    if archive.exists() or sidecar.exists():
        raise RuntimeError("refusing to overwrite R3.2A.1 protocol outputs")
    content_hashes = {
        relative: sha256_file(source)
        for relative, source in sorted(unique.items())
    }
    ledger = "".join(
        f"{digest}  {relative}\n"
        for relative, digest in content_hashes.items()
    )
    with zipfile.ZipFile(archive, "w", allowZip64=True) as handle:
        for relative, source in sorted(unique.items()):
            handle.writestr(
                _info(f"{PREFIX}/{relative}"),
                source.read_bytes(),
                zipfile.ZIP_DEFLATED,
                compresslevel=9,
            )
        handle.writestr(
            _info(f"{PREFIX}/BUNDLE_CONTENTS_SHA256.txt"),
            ledger.encode("utf-8"),
            zipfile.ZIP_DEFLATED,
            compresslevel=9,
        )
    digest = sha256_file(archive)
    sidecar.write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "PASS",
                "archive": archive.relative_to(ROOT).as_posix(),
                "sha256": digest,
                "content_files": len(unique),
                "checksum_ledger_self_entry": False,
                "external_root_reconstruction_required": False,
                "scientific_execution_performed": False,
                "G1_authorized": False,
                "next": "STRICT_FRESH_UNZIP_THEN_REPLACEMENT_TWO_PHYSICAL_HOST_G0",
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
