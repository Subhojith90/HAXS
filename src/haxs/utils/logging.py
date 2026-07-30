from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone

def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def append_log(path: str | Path, message: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(f"- {utc_now()} {message}\n")

def banner(message: str) -> str:
    line = "=" * max(8, len(message))
    return f"{line}\n{message}\n{line}"
