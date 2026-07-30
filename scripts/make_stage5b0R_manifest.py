#!/usr/bin/env python
from __future__ import annotations
import argparse, hashlib, json, datetime
from pathlib import Path
def sha(p):
    h=hashlib.sha256(); h.update(p.read_bytes()); return h.hexdigest()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--package-root',default='.'); ap.add_argument('--out',default='reproducibility/stage5b0R_manifest.json'); args=ap.parse_args()
    root=Path(args.package_root).resolve(); files=[]
    skip={'.git','.pytest_cache','__pycache__'}
    for p in sorted(root.rglob('*')):
        if not p.is_file(): continue
        rel=p.relative_to(root)
        if any(part in skip for part in rel.parts): continue
        files.append({'path':str(rel),'sha256':sha(p),'bytes':p.stat().st_size})
    out=root/args.out; out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({'stage':'stage5b0R_adaptive_trajectory_fraction_lock_mechanism_pilot','created_utc':datetime.datetime.now(datetime.UTC).isoformat(),'package_root':str(root),'file_count':len(files),'files':files},indent=2))
    print(f'stage5b0R package-wide manifest wrote {out}; files={len(files)}')
if __name__=='__main__': main()
