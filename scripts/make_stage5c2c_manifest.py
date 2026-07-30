#!/usr/bin/env python
from __future__ import annotations
import argparse, hashlib
from pathlib import Path
SKIP_DIRS = {'__pycache__', '.pytest_cache', '.git'}

def sha256(path: Path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default='.')
    ap.add_argument('--out', default='MANIFEST.sha256')
    args = ap.parse_args()
    root = Path(args.root).resolve(); out = (root / args.out).resolve()
    rows = []
    for p in sorted(root.rglob('*')):
        if not p.is_file(): continue
        if any(part in SKIP_DIRS for part in p.parts): continue
        if p.resolve() == out: continue
        rows.append(f'{sha256(p)}  {p.relative_to(root).as_posix()}')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text('\n'.join(rows) + '\n')
    print({'stage':'stage5c2c_manifest','root':str(root),'files':len(rows),'manifest':str(out.relative_to(root))})
if __name__ == '__main__': main()
