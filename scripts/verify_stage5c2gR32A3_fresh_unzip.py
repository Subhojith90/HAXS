#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import stat
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from stage5c2gR32A3_common import load_candidate, sha256_file
from verify_stage5c2gR32A3_root import verify_root

PREFIX = "HAXS_Stage5C2G_R3_2A_3_Protocol"


def verify_protocol(protocol: Path) -> dict:
    with zipfile.ZipFile(protocol) as archive:
        names = archive.namelist()
        if not names or len(names) != len(set(names)):
            raise RuntimeError("duplicate or empty protocol")
        for item in archive.infolist():
            path = PurePosixPath(item.filename)
            mode = item.external_attr >> 16
            if path.is_absolute() or ".." in path.parts or not path.parts or path.parts[0] != PREFIX or stat.S_ISLNK(mode):
                raise RuntimeError(f"unsafe protocol entry: {item.filename}")
            if "__pycache__" in path.parts or path.suffix.lower() in {".pyc", ".pyo", ".pth"}:
                raise RuntimeError(f"forbidden import artifact: {item.filename}")
        with tempfile.TemporaryDirectory(prefix="haxs-stage5c2gR32A3-fresh-") as directory:
            archive.extractall(directory)
            root = Path(directory) / PREFIX
            candidate = load_candidate(root)
            exact = verify_root(root, candidate)
            forbidden = [
                root / "results/stage5c2gR32A3/protocol/AUTHORIZATION.json",
                root / "results/stage5c2gR32A3/protocol/LOCKED.json",
                root / "results/stage5c2gR32A3/protocol/SUPERVISOR_AUTHORIZATION_G1_ONLY.json",
                root / "results/stage5c2gR32A3/state/G1.json",
            ]
            if any(path.exists() or path.is_symlink() for path in forbidden):
                raise RuntimeError("fresh protocol contains authorization or G1 state")
            return {
                "stage": "stage5c2gR32A3_fresh_unzip", "status": "PASS",
                "candidate_sha256": candidate["candidate_sha256"],
                "protocol_content_sha256": candidate["protocol_content_sha256"],
                "protocol_archive_sha256": sha256_file(protocol),
                "content_files": exact["files"], "whole_root_exact": True,
                "bytecode_closed": True, "G1_authorized": False,
                "scientific_execution_performed": False,
            }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify_protocol(args.protocol.resolve()), indent=2, sort_keys=True))
