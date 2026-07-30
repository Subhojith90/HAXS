#!/usr/bin/env python
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default='.')
    ap.add_argument('--out', default='results/stage5c2b_lite/MANIFEST.sha256')
    args = ap.parse_args()
    root = Path(args.root).resolve()
    out = root / args.out
    rows = []
    skip_parts = {'.git', '__pycache__', '.pytest_cache'}
    for p in sorted(root.rglob('*')):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        if any(part in skip_parts for part in rel.parts):
            continue
        if rel == Path(args.out):
            continue
        rows.append(f'{sha256(p)}  {rel.as_posix()}')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text('\n'.join(rows) + '\n')
    summary = {'stage': 'stage5c2b_manifest', 'root': str(root), 'files': len(rows), 'manifest': args.out}
    (out.parent / 'manifest_summary.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
if __name__ == '__main__': main()
