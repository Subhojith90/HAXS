#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2gR_common import scientific_paths, sha256_file


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="output/stage5c2gR/HAXS_Stage5C2G_R_Protocol_Review.zip")
    args = parser.parse_args()
    destination = ROOT / args.out
    destination.parent.mkdir(parents=True, exist_ok=True)
    paths = scientific_paths(ROOT)
    manifest_lines = [f"{sha256_file(path)}  {path.relative_to(ROOT).as_posix()}" for path in paths]
    with tempfile.TemporaryDirectory(prefix="stage5c2gR_source_") as name:
        manifest = Path(name) / "MANIFEST.stage5c2gR.source.sha256"
        manifest.write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
        with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in paths:
                info = zipfile.ZipInfo(f"HAXS_Stage5C2G_R_Protocol_Review/{path.relative_to(ROOT).as_posix()}", date_time=(1980, 1, 1, 0, 0, 0))
                info.external_attr = 0o100644 << 16
                archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
            info = zipfile.ZipInfo("HAXS_Stage5C2G_R_Protocol_Review/MANIFEST.stage5c2gR.source.sha256", date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            archive.writestr(info, manifest.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    sidecar = destination.with_name(destination.stem + "_SHA256.txt")
    sidecar.write_text(f"{sha256_file(destination)}  {destination.name}\n", encoding="utf-8")
    print(json.dumps({"stage": "stage5c2gR_protocol_review_package", "archive": str(destination.relative_to(ROOT)), "sha256": sha256_file(destination), "source_files": len(paths), "custody_contract": "content_addressed_external_mount"}, indent=2))


if __name__ == "__main__":
    main()

