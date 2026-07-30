#!/usr/bin/env python
from __future__ import annotations
import argparse, hashlib, sys
from pathlib import Path

def sha(p: Path):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root',default='.'); ap.add_argument('--manifest',default='MANIFEST.sha256')
    a=ap.parse_args(); root=Path(a.root).resolve(); manifest=(root/a.manifest).resolve() if not Path(a.manifest).is_absolute() else Path(a.manifest)
    bad=[]; missing=[]; checked=0
    for line in manifest.read_text().splitlines():
        if not line.strip(): continue
        exp, rel = line.split(maxsplit=1)
        p=root/rel.strip()
        if not p.exists(): missing.append(rel.strip()); continue
        checked += 1
        got=sha(p)
        if got != exp: bad.append(rel.strip())
    if bad or missing:
        print({'manifest':str(manifest),'checked':checked,'bad':bad[:20],'missing':missing[:20],'status':'FAIL'})
        sys.exit(1)
    print({'manifest':str(manifest),'checked':checked,'status':'OK'})
if __name__=='__main__': main()
