#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

PREFIX = "HAXS_Stage5C2G_R3_2A_Protocol"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", type=Path, required=True)
    args = parser.parse_args()
    with zipfile.ZipFile(args.submission) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise RuntimeError("duplicate archive entry")
        for item in archive.infolist():
            path = PurePosixPath(item.filename)
            mode = item.external_attr >> 16
            if path.is_absolute() or ".." in path.parts or stat.S_ISLNK(mode):
                raise RuntimeError("unsafe archive entry")
            if "__pycache__" in path.parts or ".pytest_cache" in path.parts:
                raise RuntimeError("cache entry forbidden")
        ledger_name = f"{PREFIX}/BUNDLE_CONTENTS_SHA256.txt"
        if ledger_name not in names:
            raise RuntimeError("checksum ledger missing")
        ledger = archive.read(ledger_name).decode("utf-8").splitlines()
        if any("BUNDLE_CONTENTS_SHA256.txt" in line for line in ledger):
            raise RuntimeError("checksum ledger contains a self-entry")
        with tempfile.TemporaryDirectory(prefix="haxs-r32a-fresh-") as directory:
            root = Path(directory)
            archive.extractall(root)
            package_root = root / PREFIX
            expected = {}
            for line in ledger:
                value, relative = line.split("  ", 1)
                expected[relative] = value
            actual = {
                path.relative_to(package_root).as_posix(): digest(path)
                for path in package_root.rglob("*")
                if path.is_file() and path.name != "BUNDLE_CONTENTS_SHA256.txt"
            }
            if actual != expected:
                raise RuntimeError("fresh-unzip content manifest mismatch")
            candidate = json.loads((package_root / "results/stage5c2gR32A/protocol/CANDIDATE.json").read_text())
            if candidate["execution_permissions"]["G1"] != "BLOCKED_PENDING_TWO_PHYSICAL_HOST_G0_SUPERVISORY_ACCEPTANCE_AND_NEW_RECEIPT":
                raise RuntimeError("fresh candidate is not fail closed")
    print(json.dumps({
        "stage": "stage5c2gR32A_fresh_unzip", "status": "PASS",
        "candidate_sha256": candidate["candidate_sha256"],
        "content_files": len(expected), "checksum_ledger_self_entry": False,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
