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
    completed = subprocess.run(command, cwd=cwd, env=environment, text=True, capture_output=True)
    print(completed.stdout, end=""); print(completed.stderr, end="", file=sys.stderr)
    if completed.returncode != 0: raise RuntimeError(f"fresh-unzip command failed: {command}")
    return completed.stdout


def main() -> None:
    if not sys.flags.isolated: raise SystemExit("fresh-unzip authorization gate requires Python isolated mode (-I)")
    parser = argparse.ArgumentParser(); parser.add_argument("--submission", required=True); parser.add_argument("--custody-root", required=True); args = parser.parse_args()
    candidate = json.loads((ROOT / "results/stage5c2gR3/protocol/CANDIDATE.json").read_text(encoding="utf-8")); expected = candidate["candidate_sha256"]
    with tempfile.TemporaryDirectory(prefix="stage5c2gR3_fresh_") as name:
        extract = Path(name) / "extract"; extract.mkdir()
        submission = Path(args.submission); submission = submission if submission.is_absolute() else ROOT / submission
        with zipfile.ZipFile(submission) as archive: safe_extract(archive, extract)
        roots = [path for path in extract.iterdir() if path.is_dir()]
        if len(roots) != 1: raise RuntimeError("archive must contain exactly one root")
        root = roots[0]; manifest = root / "MANIFEST.stage5c2gR3_1.sha256"
        packaged_candidate = json.loads((root / "CANDIDATE.stage5c2gR3_1.json").read_text(encoding="utf-8"))
        if packaged_candidate != candidate: raise RuntimeError("packaged candidate differs from the verified source candidate")
        sbom = json.loads((root / "SBOM.stage5c2gR3_1.json").read_text(encoding="utf-8"))
        if sbom.get("candidate_sha256") != expected or sbom.get("distributions") != candidate["environment"]["observed"]["packages"]: raise RuntimeError("packaged SBOM differs from candidate environment identity")
        wheel = root / "haxs-0.8.1-py3-none-any.whl"
        if digest(wheel) != candidate["installed_wheel"]["wheel_sha256"] or sbom.get("installed_wheel") != candidate["installed_wheel"]: raise RuntimeError("packaged installed wheel differs from candidate")
        expected_files = set()
        for line in manifest.read_text(encoding="utf-8").splitlines():
            expected_hash, relative = line.split("  ", 1); expected_files.add(relative)
            if digest(root / relative) != expected_hash: raise RuntimeError(f"source manifest failed: {relative}")
        actual_runtime = set(candidate["runtime_tree"]["files"])
        if expected_files != actual_runtime: raise RuntimeError("fresh archive manifest path set differs from candidate")
        dangerous = {"PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP", "PYTHONINSPECT", "PYTHONUSERBASE", "LD_PRELOAD", "DYLD_INSERT_LIBRARIES", "DYLD_LIBRARY_PATH"}
        environment = {key: value for key, value in os.environ.items() if key not in dangerous}; environment["HAXS_CUSTODY_ROOT"] = str(Path(args.custody_root).resolve())
        run([sys.executable, "-I", "scripts/check_stage5c2gR3_static_gate.py"], root, environment)
        run([sys.executable, "scripts/run_tests.py"], root, environment)
        run([sys.executable, "-I", "scripts/verify_stage5c2gR3_immutable_install.py"], root, environment)
        stdout = run([sys.executable, "-I", "scripts/verify_stage5c2gR3_protocol.py", "--custody-root", str(Path(args.custody_root).resolve())], root, environment)
        if json.loads(stdout)["candidate_sha256"] != expected: raise RuntimeError("fresh candidate differs")
    print(json.dumps({"stage": "stage5c2gR3_1_fresh_unzip", "status": "PASS", "candidate_sha256": expected}, indent=2))


if __name__ == "__main__": main()
