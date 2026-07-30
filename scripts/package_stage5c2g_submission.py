#!/usr/bin/env python
from __future__ import annotations

import hashlib
import shutil
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output/stage5c2g"
EXCLUDED_PARTS = {".git", ".venv", "__pycache__", ".pytest_cache", "install_prefix", "tmp"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def allowed(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    return path.is_file() and not any(part in EXCLUDED_PARTS for part in relative.parts) and path.suffix not in EXCLUDED_SUFFIXES and relative.parts[:2] != ("output", "stage5c2g")


def copy_file(path: Path, destination: Path) -> None:
    target = destination / path.relative_to(ROOT)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, target)


def manifest(root: Path) -> None:
    lines = [f"{sha(path)}  {path.relative_to(root).as_posix()}" for path in sorted(root.rglob("*")) if path.is_file() and path.name != "MANIFEST.sha256"]
    (root / "MANIFEST.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def archive(root: Path, destination: Path) -> None:
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as output:
        for path in sorted(root.rglob("*")):
            if path.is_file():
                output.write(path, Path(root.name) / path.relative_to(root))


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="haxs_stage5c2g_package_") as name:
        temp = Path(name)
        source = temp / "haxs_stage5c2g_clean_source"
        results = temp / "haxs_stage5c2g_results"
        source.mkdir(); results.mkdir()
        for path in sorted(ROOT.rglob("*")):
            relative = path.relative_to(ROOT)
            if allowed(path) and relative.parts[:2] != ("results", "stage5c2g") and relative.parts[:1] != ("output",):
                copy_file(path, source)
        include_roots = [ROOT / "results/stage5c2g", ROOT / "configs/stage5c2g", ROOT / "docs/stage5c2g", ROOT / "tests/stage5c2g"]
        include_files = [ROOT / "README.md", ROOT / "pyproject.toml", ROOT / "src/haxs/methods/constrained_spin_hole.py", ROOT / "src/haxs/methods/dtwa.py", ROOT / "src/haxs/validation/topology.py"] + sorted((ROOT / "scripts").glob("*stage5c2g*.py")) + [ROOT / "scripts/verify_manifest.py"]
        for base in include_roots:
            for path in sorted(base.rglob("*")):
                if allowed(path):
                    copy_file(path, results)
        for path in include_files:
            if allowed(path):
                copy_file(path, results)
        manifest(source); manifest(results)
        source_zip = OUTPUT / "haxs_stage5c2g_clean_source.zip"
        results_zip = OUTPUT / "haxs_stage5c2g_results.zip"
        archive(source, source_zip); archive(results, results_zip)
    checksums = [f"{sha(path)}  {path.name}" for path in (source_zip, results_zip)]
    (OUTPUT / "SHA256SUMS.txt").write_text("\n".join(checksums) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
