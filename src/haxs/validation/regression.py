from __future__ import annotations
from pathlib import Path
from haxs.io.hashes import sha256_file

def regression_hash(path: str | Path) -> dict[str, str]:
    return {"path": str(path), "sha256": sha256_file(path)}

def file_exists(path: str | Path) -> dict[str, object]:
    p = Path(path)
    return {"path": str(path), "exists": p.exists(), "size": p.stat().st_size if p.exists() else 0}
