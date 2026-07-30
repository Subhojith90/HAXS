#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

EXCLUDED_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", "install_prefix"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--out", default="MANIFEST.stage5c2g.sha256")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    output = root / args.out
    lines = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path == output:
            continue
        relative = path.relative_to(root)
        if any(part in EXCLUDED_DIRS for part in relative.parts) or path.suffix in EXCLUDED_SUFFIXES:
            continue
        lines.append(f"{digest(path)}  {relative.as_posix()}")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print({"stage": "stage5c2g_root_relative_manifest", "files": len(lines), "manifest": str(output)})


if __name__ == "__main__":
    main()

