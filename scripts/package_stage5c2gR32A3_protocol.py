#!/usr/bin/env python
from __future__ import annotations

import json
import stat
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_stage5c2gR32A3_candidate import closure_paths, runtime_paths
from stage5c2gR32A3_common import safe_relative, sha256_file

PREFIX = "HAXS_Stage5C2G_R3_2A_3_Protocol"


def info(name: str) -> zipfile.ZipInfo:
    item = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    item.external_attr = (stat.S_IFREG | 0o644) << 16
    return item


def main() -> None:
    output = ROOT / "output/stage5c2gR32A3"
    required = [
        ROOT / "results/stage5c2gR32A3/protocol/CANDIDATE.json",
        ROOT / "results/stage5c2gR32A3/protocol/NAMED_TEST_LEDGER.json",
        ROOT / "results/stage5c2gR32A3/protocol/ROOT_MANIFEST.json",
        ROOT / "results/stage5c2gR32A3/environment.json",
        ROOT / "results/stage5c2gR32A3/adversarial/OUTCOMES.json",
        ROOT / "output/stage5c2gR32A3/haxs-0.8.6-py3-none-any.whl",
    ]
    sources = [*runtime_paths(), *closure_paths(), *required]
    wheelhouse = ROOT / "ci/frozen/stage5c2gR32A2/WHEELHOUSE_MANIFEST_SHA256.txt"
    for line in wheelhouse.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        path = ROOT / safe_relative(relative)
        if sha256_file(path) != digest:
            raise RuntimeError(f"wheelhouse input failed: {relative}")
        sources.append(path)
    for directory in [ROOT / "output/stage5c2gR32A/g1_preflight", ROOT / "output/stage5c2gR32A/s03_development", ROOT / "output/stage5c2gR32A/s03_validation"]:
        sources.extend(path for path in sorted(directory.rglob("*")) if path.is_file() and not path.is_symlink() and "__pycache__" not in path.parts)
    unique = {path.relative_to(ROOT).as_posix(): path for path in sources}
    if any("__pycache__" in Path(name).parts or Path(name).suffix.lower() in {".pyc", ".pyo", ".pth"} for name in unique):
        raise RuntimeError("protocol source contains forbidden import artifact")
    archive = output / f"{PREFIX}.zip"
    sidecar = output / f"{PREFIX}_SHA256.txt"
    if archive.exists() or sidecar.exists():
        raise RuntimeError("refusing to overwrite R3.2A.3 protocol")
    hashes = {name: sha256_file(path) for name, path in sorted(unique.items())}
    ledger = "".join(f"{digest}  {name}\n" for name, digest in hashes.items())
    with zipfile.ZipFile(archive, "w", allowZip64=True) as handle:
        for name, path in sorted(unique.items()):
            handle.writestr(info(f"{PREFIX}/{name}"), path.read_bytes(), zipfile.ZIP_DEFLATED, compresslevel=9)
        handle.writestr(info(f"{PREFIX}/BUNDLE_CONTENTS_SHA256.txt"), ledger.encode(), zipfile.ZIP_DEFLATED, compresslevel=9)
    digest = sha256_file(archive)
    sidecar.write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    print(json.dumps({"stage": "stage5c2gR32A3_protocol", "status": "PASS", "archive": str(archive), "sha256": digest, "content_files": len(unique), "G1_authorized": False, "scientific_execution_performed": False}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
