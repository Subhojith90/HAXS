#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

EXCLUDED_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}
EXCLUDED_FILES = {"MANIFEST.sha256", "MANIFEST.source.sha256"}


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="MANIFEST.sha256")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    output = root / args.out
    lines = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in EXCLUDED_DIRS for part in relative.parts):
            continue
        if path.suffix in EXCLUDED_SUFFIXES or relative.as_posix() in EXCLUDED_FILES:
            continue
        lines.append(f"{digest(path)}  {relative.as_posix()}")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print({"stage": "stage5c2f_root_relative_manifest", "files": len(lines), "manifest": output.name})


if __name__ == "__main__":
    main()
