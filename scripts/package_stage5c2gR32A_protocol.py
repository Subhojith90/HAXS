#!/usr/bin/env python
from __future__ import annotations

import hashlib
import json
import stat
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_stage5c2gR32A_candidate import runtime_paths
from stage5c2gR32_common import sha256_file

PREFIX = "HAXS_Stage5C2G_R3_2A_Protocol"


def _info(name: str) -> zipfile.ZipInfo:
    item = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    item.external_attr = (stat.S_IFREG | 0o644) << 16
    return item


def main() -> None:
    output = ROOT / "output/stage5c2gR32A"
    candidate = ROOT / "results/stage5c2gR32A/protocol/CANDIDATE.json"
    wheel = output / "haxs-0.8.3-py3-none-any.whl"
    environment = ROOT / "results/stage5c2gR32A/environment.json"
    required = [candidate, wheel, environment]
    if not all(path.is_file() for path in required):
        raise RuntimeError("candidate, wheel, and environment are required")
    sources: list[tuple[Path, str]] = [
        *[(path, path.relative_to(ROOT).as_posix()) for path in runtime_paths()],
        (candidate, candidate.relative_to(ROOT).as_posix()),
        (wheel, wheel.relative_to(ROOT).as_posix()),
        (environment, environment.relative_to(ROOT).as_posix()),
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
    ]:
        for path in sorted(directory.rglob("*")):
            if path.is_file() and not path.is_symlink() and "__pycache__" not in path.parts:
                sources.append((path, path.relative_to(ROOT).as_posix()))
    unique = {relative: source for source, relative in sources}
    if any(Path(relative).is_absolute() or ".." in Path(relative).parts for relative in unique):
        raise RuntimeError("package contains an unsafe path")
    archive = output / f"{PREFIX}.zip"
    if archive.exists():
        raise RuntimeError("refusing to overwrite protocol archive")
    content_hashes = {relative: sha256_file(source) for relative, source in sorted(unique.items())}
    ledger = "".join(f"{digest}  {relative}\n" for relative, digest in content_hashes.items())
    with zipfile.ZipFile(archive, "w", allowZip64=True) as handle:
        for relative, source in sorted(unique.items()):
            handle.writestr(_info(f"{PREFIX}/{relative}"), source.read_bytes(), zipfile.ZIP_DEFLATED, compresslevel=9)
        # Deliberately excluded from its own content list.
        handle.writestr(_info(f"{PREFIX}/BUNDLE_CONTENTS_SHA256.txt"), ledger.encode("utf-8"), zipfile.ZIP_DEFLATED, compresslevel=9)
    digest = sha256_file(archive)
    sidecar = output / f"{PREFIX}_SHA256.txt"
    sidecar.write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    print(json.dumps({
        "status": "PASS", "archive": archive.relative_to(ROOT).as_posix(),
        "sha256": digest, "content_files": len(unique),
        "checksum_ledger_self_entry": False,
        "scientific_execution_performed": False,
        "next": "FRESH_UNZIP_THEN_TWO_PHYSICAL_HOST_G0",
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
