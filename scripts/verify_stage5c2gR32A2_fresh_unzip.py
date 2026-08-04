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
from stage5c2gR32A2_common import load_candidate, sha256_file
from verify_stage5c2gR32A2_root import verify_root

PREFIX = "HAXS_Stage5C2G_R3_2A_2_Protocol"


def verify_protocol(protocol: Path) -> dict:
    if not protocol.is_file() or protocol.is_symlink():
        raise RuntimeError("protocol archive is missing or unsafe")
    with zipfile.ZipFile(protocol) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise RuntimeError("duplicate protocol archive entry")
        for item in archive.infolist():
            path = PurePosixPath(item.filename)
            mode = item.external_attr >> 16
            if path.is_absolute() or ".." in path.parts or stat.S_ISLNK(mode) or not path.parts or path.parts[0] != PREFIX:
                raise RuntimeError(f"unsafe protocol entry: {item.filename}")
            if "__pycache__" in path.parts or path.suffix.lower() in {".pyc", ".pyo", ".pth"}:
                raise RuntimeError(f"forbidden import artifact in protocol: {item.filename}")
        with tempfile.TemporaryDirectory(prefix="haxs-stage5c2gR32A2-fresh-") as directory:
            temporary = Path(directory)
            archive.extractall(temporary)
            extracted = temporary / PREFIX
            candidate = load_candidate(extracted)
            result = verify_root(extracted, candidate)
            if candidate["execution_permissions"]["G1"] != "BLOCKED_PENDING_NEW_SUPERVISORY_REVIEW_AND_RECEIPT":
                raise RuntimeError("fresh candidate is not fail closed")
            forbidden = [
                extracted / "results/stage5c2gR32A2/protocol/AUTHORIZATION.json",
                extracted / "results/stage5c2gR32A2/protocol/LOCKED.json",
                extracted / "results/stage5c2gR32A2/protocol/SUPERVISOR_AUTHORIZATION_G1_ONLY.json",
                extracted / "results/stage5c2gR32A2/state/G1.json",
            ]
            if any(path.exists() or path.is_symlink() for path in forbidden):
                raise RuntimeError("fresh protocol contains forbidden authorization or G1 state")
            return {
                "stage": "stage5c2gR32A2_fresh_unzip", "status": "PASS",
                "candidate_sha256": candidate["candidate_sha256"],
                "protocol_archive_sha256": sha256_file(protocol),
                "content_files": result["files"], "whole_root_exact": True,
                "bytecode_closed": True, "G1_authorized": False,
                "scientific_execution_performed": False,
            }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify_protocol(args.protocol.resolve()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
