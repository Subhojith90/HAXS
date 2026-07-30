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
        if destination.resolve() not in target.parents and target != destination.resolve(): raise RuntimeError("unsafe archive path")
        if (info.external_attr >> 16) & 0o170000 == 0o120000: raise RuntimeError("symbolic links are forbidden")
    archive.extractall(destination)


def run(command: list[str], cwd: Path, env: dict | None = None) -> str:
    completed = subprocess.run(command, cwd=cwd, text=True, capture_output=True, env=env)
    print(completed.stdout, end=""); print(completed.stderr, end="", file=sys.stderr)
    if completed.returncode != 0: raise RuntimeError(f"fresh-unzip command failed: {command}")
    return completed.stdout


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", required=True)
    parser.add_argument("--custody-root", default=str(ROOT))
    parser.add_argument("--expected-candidate", default="results/stage5c2gR/protocol_lock/CANDIDATE.json")
    args = parser.parse_args()
    submission = Path(args.submission).resolve()
    expected = json.loads((ROOT / args.expected_candidate).read_text(encoding="utf-8"))["candidate_sha256"]
    with tempfile.TemporaryDirectory(prefix="stage5c2gR_fresh_unzip_") as name:
        extract = Path(name) / "extract"; extract.mkdir()
        with zipfile.ZipFile(submission) as archive: safe_extract(archive, extract)
        roots = [path for path in extract.iterdir() if path.is_dir()]
        if len(roots) != 1: raise RuntimeError("submission must contain one root directory")
        root = roots[0]
        manifest = root / "MANIFEST.stage5c2gR.source.sha256"
        for line in manifest.read_text(encoding="utf-8").splitlines():
            expected_hash, relative = line.split("  ", 1)
            if digest(root / relative) != expected_hash: raise RuntimeError(f"source manifest mismatch: {relative}")
        environment = os.environ.copy(); environment["HAXS_CUSTODY_ROOT"] = str(Path(args.custody_root).resolve())
        run([sys.executable, "scripts/run_tests.py"], root, environment)
        run([sys.executable, "scripts/check_stage5c2gR_invariants.py", "--planned"], root, environment)
        stdout = run([sys.executable, "scripts/verify_stage5c2gR_protocol_lock.py", "--config", "configs/stage5c2gR/protocol.yaml", "--custody-root", str(Path(args.custody_root).resolve())], root)
        reconstructed = json.loads(stdout)["candidate_sha256"]
        if reconstructed != expected: raise RuntimeError(f"fresh candidate mismatch: {reconstructed} != {expected}")
    print(json.dumps({"stage": "stage5c2gR_fresh_unzip_gate", "status": "PASS", "candidate_sha256": expected, "custody_contract": "content_addressed_external_mount"}, indent=2))


if __name__ == "__main__":
    main()
