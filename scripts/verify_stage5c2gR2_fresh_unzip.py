#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    value = hashlib.sha256(); value.update(path.read_bytes()); return value.hexdigest()


def safe_extract(archive: zipfile.ZipFile, destination: Path) -> None:
    for info in archive.infolist():
        target = (destination / info.filename).resolve()
        if destination.resolve() not in target.parents: raise RuntimeError("unsafe archive path")
        if (info.external_attr >> 16) & 0o170000 == 0o120000: raise RuntimeError("symlink forbidden")
    archive.extractall(destination)


def run(command: list[str], cwd: Path, environment: dict) -> str:
    completed = subprocess.run(command, cwd=cwd, env=environment, text=True, capture_output=True); print(completed.stdout, end=""); print(completed.stderr, end="", file=sys.stderr)
    if completed.returncode != 0: raise RuntimeError(f"fresh-unzip command failed: {command}")
    return completed.stdout


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--submission", default="output/stage5c2gR2/HAXS_Stage5C2G_R2_Protocol.zip"); parser.add_argument("--custody-root", default=str(ROOT)); args = parser.parse_args()
    expected = json.loads((ROOT / "results/stage5c2gR2/protocol/CANDIDATE.json").read_text(encoding="utf-8"))["candidate_sha256"]
    with tempfile.TemporaryDirectory(prefix="stage5c2gR2_fresh_") as name:
        extract = Path(name) / "extract"; extract.mkdir()
        with zipfile.ZipFile(ROOT / args.submission) as archive: safe_extract(archive, extract)
        roots = [path for path in extract.iterdir() if path.is_dir()]
        if len(roots) != 1: raise RuntimeError("archive must contain one root")
        root = roots[0]; manifest = root / "MANIFEST.stage5c2gR2.sha256"
        for line in manifest.read_text(encoding="utf-8").splitlines():
            expected_hash, relative = line.split("  ", 1)
            if digest(root / relative) != expected_hash: raise RuntimeError(f"source manifest failed: {relative}")
        environment = os.environ.copy(); environment["HAXS_CUSTODY_ROOT"] = str(Path(args.custody_root).resolve())
        run([sys.executable, "scripts/run_tests.py"], root, environment)
        stdout = run([sys.executable, "scripts/verify_stage5c2gR2_protocol.py", "--custody-root", str(Path(args.custody_root).resolve())], root, environment)
        reconstructed = json.loads(stdout)["candidate_sha256"]
        if reconstructed != expected: raise RuntimeError("fresh candidate differs")
    print(json.dumps({"stage": "stage5c2gR2_fresh_unzip", "status": "PASS", "candidate_sha256": expected}, indent=2))


if __name__ == "__main__": main()

