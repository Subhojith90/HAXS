#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2gR2_common import discover_runtime_files, sha256_file


def main() -> None:
    if len(sys.argv) != 1: raise SystemExit("R2 packaging accepts no file-selection overrides")
    output = ROOT / "output/stage5c2gR2"; output.mkdir(parents=True, exist_ok=True)
    destination = output / "HAXS_Stage5C2G_R2_Protocol.zip"; paths = discover_runtime_files(ROOT)
    manifest_lines = [f"{sha256_file(path)}  {path.relative_to(ROOT).as_posix()}" for path in paths]
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in paths:
            info = zipfile.ZipInfo(f"HAXS_Stage5C2G_R2_Protocol/{path.relative_to(ROOT).as_posix()}", date_time=(1980, 1, 1, 0, 0, 0)); info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        info = zipfile.ZipInfo("HAXS_Stage5C2G_R2_Protocol/MANIFEST.stage5c2gR2.sha256", date_time=(1980, 1, 1, 0, 0, 0)); info.external_attr = 0o100644 << 16
        archive.writestr(info, ("\n".join(manifest_lines) + "\n").encode(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    sidecar = output / "HAXS_Stage5C2G_R2_Protocol_SHA256.txt"; sidecar.write_text(f"{sha256_file(destination)}  {destination.name}\n", encoding="utf-8")
    print(json.dumps({"archive": str(destination.relative_to(ROOT)), "sha256": sha256_file(destination), "runtime_files": len(paths)}, indent=2))


if __name__ == "__main__": main()

