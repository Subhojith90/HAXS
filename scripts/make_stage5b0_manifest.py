#!/usr/bin/env python
from __future__ import annotations
import argparse, hashlib, json, datetime, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha256(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--package-root',default='.'); ap.add_argument('--out',default='reproducibility/stage5b0_manifest.json'); args=ap.parse_args()
    root=(ROOT/args.package_root).resolve(); out=ROOT/args.out; out.parent.mkdir(parents=True,exist_ok=True)
    skip={'__pycache__','.pytest_cache','.git'}; files=[]
    for p in sorted(root.rglob('*')):
        if not p.is_file(): continue
        rel=p.relative_to(root).as_posix()
        if any(part in skip for part in p.parts): continue
        if rel==Path(args.out).as_posix(): continue
        files.append({'path':rel,'size_bytes':p.stat().st_size,'sha256':sha256(p)})
    out.write_text(json.dumps({'stage':'stage5b0_trajectory_fraction_lock_mechanism_pilot','created_utc':datetime.datetime.now(datetime.UTC).isoformat(),'package_root':str(root),'file_count':len(files),'files':files},indent=2))
    print(f'stage5b0 package-wide manifest wrote {out}; files={len(files)}')
if __name__=='__main__': main()
