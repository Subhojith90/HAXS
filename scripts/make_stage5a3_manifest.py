#!/usr/bin/env python
from pathlib import Path
import argparse, hashlib, json, datetime
ROOT=Path(__file__).resolve().parents[1]
def sha(p):
    h=hashlib.sha256(); h.update(Path(p).read_bytes()); return h.hexdigest()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--package-root',default='.'); ap.add_argument('--out',default='reproducibility/stage5a3_manifest.json'); args=ap.parse_args()
    root=(ROOT/args.package_root).resolve(); files=[]
    skip={'.git','__pycache__','.pytest_cache'}
    for p in root.rglob('*'):
        if not p.is_file(): continue
        if any(part in skip for part in p.parts): continue
        if p.name.endswith('.pyc'): continue
        rel=str(p.relative_to(root))
        files.append({'path':rel,'sha256':sha(p),'bytes':p.stat().st_size})
    out=ROOT/args.out; out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({'stage':'stage5a3_final_replication_lock','created_utc':datetime.datetime.utcnow().isoformat()+'Z','package_root':str(root),'file_count':len(files),'files':files},indent=2))
    print(f'stage5a3 package-wide manifest wrote {out}; files={len(files)}')
if __name__=='__main__': main()
