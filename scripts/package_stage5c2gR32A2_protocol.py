#!/usr/bin/env python
from __future__ import annotations

import json
import stat
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_stage5c2gR32A2_candidate import closure_paths, runtime_paths
from stage5c2gR32A2_common import safe_relative, sha256_file

PREFIX = "HAXS_Stage5C2G_R3_2A_2_Protocol"


def info(name: str) -> zipfile.ZipInfo:
    item = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    item.external_attr = (stat.S_IFREG | 0o644) << 16
    return item


def main() -> None:
    output = ROOT / "output/stage5c2gR32A2"
    required = [
        ROOT / "results/stage5c2gR32A2/protocol/CANDIDATE.json",
        ROOT / "results/stage5c2gR32A2/protocol/NAMED_TEST_LEDGER.json",
        ROOT / "results/stage5c2gR32A2/protocol/ROOT_MANIFEST.json",
        ROOT / "results/stage5c2gR32A2/protocol/SUPERSESSION.json",
        ROOT / "results/stage5c2gR32A2/environment.json",
        ROOT / "output/stage5c2gR32A2/haxs-0.8.5-py3-none-any.whl",
    ]
    if any(not path.is_file() or path.is_symlink() for path in required):
        raise RuntimeError("R3.2A.2 generated candidate inputs are missing or unsafe")
    sources = [*runtime_paths(), *closure_paths(), *required]
    wheelhouse_manifest = ROOT / "ci/frozen/stage5c2gR32A2/WHEELHOUSE_MANIFEST_SHA256.txt"
    for line in wheelhouse_manifest.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        path = ROOT / safe_relative(relative)
        if not path.is_file() or path.is_symlink() or sha256_file(path) != digest:
            raise RuntimeError(f"frozen wheelhouse input failed: {relative}")
        sources.append(path)
    for directory in [ROOT / "output/stage5c2gR32A/g1_preflight", ROOT / "output/stage5c2gR32A/s03_development", ROOT / "output/stage5c2gR32A/s03_validation"]:
        for path in sorted(directory.rglob("*")):
            if path.is_file() and not path.is_symlink() and "__pycache__" not in path.parts:
                sources.append(path)
    for directory in [
        ROOT / "results/stage5c2gR32A2/transcripts",
        ROOT / "results/stage5c2gR32A2/junit",
        ROOT / "results/stage5c2gR32A2/adversarial",
        ROOT / "results/stage5c2gR32A2/development",
    ]:
        if directory.is_dir():
            for path in sorted(directory.rglob("*")):
                if path.is_file() and not path.is_symlink() and "__pycache__" not in path.parts and path.suffix.lower() not in {".pyc", ".pyo"}:
                    sources.append(path)
    unique = {path.relative_to(ROOT).as_posix(): path for path in sources}
    if any("__pycache__" in Path(relative).parts or Path(relative).suffix.lower() in {".pyc", ".pyo", ".pth"} for relative in unique):
        raise RuntimeError("clean protocol source set contains bytecode/import cache")
    archive = output / f"{PREFIX}.zip"
    sidecar = output / f"{PREFIX}_SHA256.txt"
    if archive.exists() or sidecar.exists():
        raise RuntimeError("refusing to overwrite R3.2A.2 protocol outputs")
    output.mkdir(parents=True, exist_ok=True)
    hashes = {relative: sha256_file(path) for relative, path in sorted(unique.items())}
    ledger = "".join(f"{digest}  {relative}\n" for relative, digest in hashes.items())
    with zipfile.ZipFile(archive, "w", allowZip64=True) as handle:
        for relative, path in sorted(unique.items()):
            handle.writestr(info(f"{PREFIX}/{relative}"), path.read_bytes(), zipfile.ZIP_DEFLATED, compresslevel=9)
        handle.writestr(info(f"{PREFIX}/BUNDLE_CONTENTS_SHA256.txt"), ledger.encode("utf-8"), zipfile.ZIP_DEFLATED, compresslevel=9)
    digest = sha256_file(archive)
    sidecar.write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    print(json.dumps({
        "stage": "stage5c2gR32A2_protocol", "status": "PASS",
        "archive": archive.relative_to(ROOT).as_posix(), "sha256": digest,
        "content_files": len(unique), "bytecode_caches": 0,
        "scientific_execution_performed": False, "G1_authorized": False,
        "next": "STRICT_FRESH_UNZIP_THEN_REPLACEMENT_TWO_HOST_G0",
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
