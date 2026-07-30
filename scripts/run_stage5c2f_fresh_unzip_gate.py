#!/usr/bin/env python
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {".git", ".venv", "__pycache__", ".pytest_cache"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args()
    temp = Path(tempfile.mkdtemp(prefix="haxs_stage5c2f_fresh_unzip_"))
    archive = temp / "source.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as handle:
        for path in sorted(ROOT.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(ROOT)
            if any(part in EXCLUDED for part in relative.parts) or path.suffix in {".pyc", ".pyo"}:
                continue
            if relative.parts[:2] in {("results", "stage5c2f"), ("results", "stage5c2g")}:
                continue
            handle.write(path, Path("haxs_stage5c2f_occupancy_preserving_relock_v1") / relative)
    extract = temp / "extract"
    with zipfile.ZipFile(archive) as handle:
        handle.extractall(extract)
    package = extract / "haxs_stage5c2f_occupancy_preserving_relock_v1"
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    command = [sys.executable, "scripts/run_stage5c2f_all.py", "--preflight"]
    completed = subprocess.run(command, cwd=package, env=env)
    if args.keep:
        print(f"fresh-unzip workspace retained at {temp}")
    elif completed.returncode == 0:
        import shutil
        shutil.rmtree(temp)
    completed.check_returncode()
    print("Stage 5C.2F fresh-unzip artifact gate: PASS")


if __name__ == "__main__":
    main()
