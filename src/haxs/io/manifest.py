from __future__ import annotations
import json, platform, sys, subprocess
from pathlib import Path
from datetime import datetime, timezone
from haxs.io.hashes import sha256_file, hash_dict

def package_versions() -> dict[str, str]:
    mods = ["numpy", "scipy", "pandas", "matplotlib", "yaml", "pytest"]
    out = {}
    for m in mods:
        try:
            mod = __import__(m)
            out[m] = str(getattr(mod, "__version__", "available"))
        except Exception as exc:
            out[m] = f"unavailable: {exc}"
    return out

def pseudo_commit(root: str | Path) -> str:
    paths = [p for p in Path(root).rglob("*") if p.is_file() and ".git" not in p.parts]
    payload = "".join(sorted(str(p.relative_to(root)) for p in paths)).encode("utf-8")
    return hash_dict({"files": payload.hex()})

def collect_manifest(root: str | Path, decision_status: str = "unknown", tests: dict | None = None, commands: list[str] | None = None) -> dict:
    root = Path(root)
    key_files = []
    for sub in ["results", "figures", "tables", "manuscript", "reproducibility", "configs"]:
        if (root/sub).exists():
            key_files.extend([p for p in (root/sub).rglob("*") if p.is_file()])
    hashes = {str(p.relative_to(root)): sha256_file(p) for p in sorted(key_files)}
    result_hashes = {k: v for k, v in hashes.items() if k.startswith("results/") or k.startswith("tables/")}
    figure_hashes = {k: v for k, v in hashes.items() if k.startswith("figures/") and k.endswith(".png")}
    report_path = root / "manuscript" / "main.pdf"
    transcript = root / "reproducibility" / "test_transcript.txt"
    transcript_text = transcript.read_text(encoding="utf-8") if transcript.exists() else ""
    config_files = [str(p.relative_to(root)) for p in sorted((root/"configs").rglob("*.yaml"))] if (root/"configs").exists() else []
    return {
        "timestamp_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "pseudo_commit": pseudo_commit(root),
        "python_version": sys.version,
        "platform": platform.platform(),
        "package_versions": package_versions(),
        "random_seeds": [1729, 31415, 27182, 101, 102, 103, 104],
        "config_files_used": config_files,
        "commands": commands or [],
        "file_hashes": hashes,
        "result_file_hashes": result_hashes,
        "figure_file_hashes": figure_hashes,
        "report_hash": sha256_file(report_path) if report_path.exists() else None,
        "tests": tests or {},
        "tests_passed": (" passed" in transcript_text and "failed" not in transcript_text.lower()),
        "decision_status": decision_status,
    }

def write_manifest(path: str | Path, manifest: dict) -> None:
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
