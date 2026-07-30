#!/usr/bin/env python
from __future__ import annotations

import hashlib
import shutil
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "stage5c2f"
EXCLUDED_PARTS = {".git", ".venv", "__pycache__", ".pytest_cache", "install_prefix"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def allowed(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    if any(part in EXCLUDED_PARTS for part in relative.parts) or path.suffix in EXCLUDED_SUFFIXES:
        return False
    if relative.parts and relative.parts[0] == "output":
        return False
    if path.name.startswith("haxs_stage5c2eR_dominant_variance_relock_checkpoint_"):
        return False
    return True


def write_manifest(root: Path) -> None:
    lines = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "MANIFEST.sha256":
            lines.append(f"{sha256(path)}  {path.relative_to(root).as_posix()}")
    (root / "MANIFEST.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def zip_tree(source: Path, destination: Path) -> None:
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(source.rglob("*")):
            if path.is_file():
                archive.write(path, Path(source.name) / path.relative_to(source))


def build_source(stage: Path) -> None:
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or not allowed(path):
            continue
        relative = path.relative_to(ROOT)
        if relative.parts[:2] == ("results", "stage5c2f"):
            continue
        target = stage / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def build_results(stage: Path) -> None:
    include_roots = [
        ROOT / "results" / "stage5c2f",
        ROOT / "results" / "stage5c2d_lite" / "confirmation",
        ROOT / "configs" / "stage5c2f",
        ROOT / "docs" / "stage5c2f",
        ROOT / "tests" / "stage5c2f",
    ]
    include_files = [ROOT / "README.md", ROOT / "pyproject.toml"] + sorted((ROOT / "scripts").glob("*stage5c2f*.py")) + [ROOT / "scripts" / "verify_manifest.py"]
    for base in include_roots:
        for path in sorted(base.rglob("*")):
            if path.is_file() and allowed(path):
                relative = path.relative_to(ROOT)
                target = stage / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
    for path in include_files:
        if path.is_file() and allowed(path):
            target = stage / path.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="haxs_stage5c2f_package_") as temp_name:
        temp = Path(temp_name)
        source = temp / "haxs_stage5c2f_clean_source"
        results = temp / "haxs_stage5c2f_results"
        source.mkdir(); results.mkdir()
        build_source(source); build_results(results)
        write_manifest(source); write_manifest(results)
        source_zip = OUTPUT / "haxs_stage5c2f_clean_source.zip"
        results_zip = OUTPUT / "haxs_stage5c2f_results.zip"
        zip_tree(source, source_zip); zip_tree(results, results_zip)
    checksum_lines = [f"{sha256(path)}  {path.name}" for path in (source_zip, results_zip)]
    (OUTPUT / "SHA256SUMS.txt").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
    print({"source": str(source_zip), "results": str(results_zip), "checksums": str(OUTPUT / "SHA256SUMS.txt")})


if __name__ == "__main__":
    main()
