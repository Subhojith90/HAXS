#!/usr/bin/env python
from __future__ import annotations
import argparse, hashlib
from pathlib import Path

EXCLUDE_DIRS={'.git','.venv','__pycache__','.pytest_cache'}
EXCLUDE_SUFFIXES={'.pyc','.pyo'}

def sha(p: Path):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

def iter_files(root: Path):
    for p in sorted(root.rglob('*')):
        if not p.is_file(): continue
        rel=p.relative_to(root)
        if any(part in EXCLUDE_DIRS for part in rel.parts): continue
        if p.suffix in EXCLUDE_SUFFIXES: continue
        if rel.as_posix() in {'MANIFEST.sha256','MANIFEST.source.sha256'}: continue
        yield p

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root',default='.'); ap.add_argument('--out',default='MANIFEST.sha256')
    a=ap.parse_args(); root=Path(a.root).resolve(); out=(root/a.out).resolve() if not Path(a.out).is_absolute() else Path(a.out)
    lines=[]
    for p in iter_files(root):
        lines.append(f'{sha(p)}  {p.relative_to(root).as_posix()}')
    out.parent.mkdir(parents=True, exist_ok=True); out.write_text('\n'.join(lines)+'\n')
    print({'stage':'stage5c2eR_manifest','root':str(root),'files':len(lines),'manifest':str(out)})
if __name__=='__main__': main()
