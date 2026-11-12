#!/usr/bin/env python3
"""Fail-closed preflight for the HAXS Zenodo/GitHub release."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_AUTHORS = [
    "Halder, Subhojit",
    "Ganguly, Shreyosha",
    "Masta, Apoorv Kumar",
    "Devendrababu, Shalini",
    "Riaz, Farina",
    "Ganguly, Srinjoy",
]
EXPECTED_ORCIDS = {
    "Halder, Subhojit": "0000-0002-9875-0357",
    "Devendrababu, Shalini": "0009-0007-2856-953X",
    "Ganguly, Srinjoy": "0000-0003-4401-2903",
}
REQUIRED_PATHS = [
    ".zenodo.json",
    "CITATION.cff",
    "LICENSE",
    "RIGHTS.md",
    "docs/ZENODO_GITHUB_RELEASE.md",
    "docs/releases/v1.0.0.md",
    "publication_assets/README.md",
    "publication_assets/make_figures.py",
    "publication_assets/figures/dynamics_and_contrast.pdf",
    "publication_assets/figures/occupancy_effects.pdf",
    "publication_assets/figures/small_system_validation.pdf",
    "publication_assets/source_data/raw/primary_curves.csv",
    "publication_assets/source_data/raw/primary_finals.csv",
    "publication_assets/source_data/raw/confirmation_curves.csv",
    "publication_assets/source_data/raw/confirmation_finals.csv",
    "publication_assets/source_data/raw/ed_dtwa_curve.csv",
    "publication_assets/source_data/raw/ed_dtwa_gates.csv",
    "output/stage5c2f/haxs_stage5c2f_results.zip",
    "output/stage5c2f/haxs_stage5c2f_clean_source.zip",
    "publication/closure_release_20260903/MANIFEST_SHA256.txt",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    missing = [path for path in REQUIRED_PATHS if not (ROOT / path).is_file()]
    if missing:
        raise RuntimeError(f"required release files missing: {missing}")

    metadata = json.loads((ROOT / ".zenodo.json").read_text(encoding="utf-8"))
    if metadata.get("upload_type") != "software":
        raise RuntimeError("Zenodo upload_type must be software")
    if metadata.get("version") != "1.0.0":
        raise RuntimeError("Zenodo version must be 1.0.0")
    if metadata.get("access_right") != "open":
        raise RuntimeError("Zenodo access_right must be open")
    if metadata.get("license") != "mit":
        raise RuntimeError("Zenodo primary software license must be mit")
    creators = metadata.get("creators", [])
    names = [creator.get("name") for creator in creators]
    if names != EXPECTED_AUTHORS:
        raise RuntimeError(f"creator order mismatch: {names}")
    for name, expected in EXPECTED_ORCIDS.items():
        actual = next(item for item in creators if item["name"] == name).get("orcid")
        if actual != expected:
            raise RuntimeError(f"ORCID mismatch for {name}: {actual}")

    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    for token in ("version: 1.0.0", "type: software", "repository-code:"):
        if token not in citation:
            raise RuntimeError(f"CITATION.cff missing {token!r}")
    if "{{" in citation or "}}" in citation:
        raise RuntimeError("CITATION.cff contains unresolved template markers")

    tracked_private = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "--", "manuscript", "deliverables"],
        text=True,
        capture_output=True,
        check=True,
    ).stdout.splitlines()
    if tracked_private:
        raise RuntimeError(f"manuscript/deliverable files must not be tracked: {tracked_private}")

    payload = {
        "citation_cff_sha256": sha256(ROOT / "CITATION.cff"),
        "creators": len(creators),
        "primary_curves_sha256": sha256(
            ROOT / "publication_assets/source_data/raw/primary_curves.csv"
        ),
        "publication_assets_files": sum(
            1 for path in (ROOT / "publication_assets").rglob("*") if path.is_file()
        ),
        "required_files": len(REQUIRED_PATHS),
        "status": "PASS",
        "version": metadata["version"],
        "zenodo_json_sha256": sha256(ROOT / ".zenodo.json"),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
