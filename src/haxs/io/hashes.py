from __future__ import annotations
import hashlib, json
from pathlib import Path

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def hash_dict(data: dict) -> str:
    payload = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
    return sha256_bytes(payload)[:16]

def write_sha256_listing(root: str | Path, out_path: str | Path, patterns=("*.py","*.yaml","*.json","*.csv","*.png","*.pdf","*.tex","*.md","*.txt")) -> None:
    base = Path(root)
    files = []
    for pattern in patterns:
        files.extend(base.rglob(pattern))
    lines = []
    for p in sorted(set(files)):
        if p.is_file() and p != Path(out_path):
            lines.append(f"{sha256_file(p)}  {p.relative_to(base)}")
    Path(out_path).write_text("\n".join(lines) + "\n", encoding="utf-8")
