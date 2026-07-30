#!/usr/bin/env python
from pathlib import Path
import argparse, hashlib, json, datetime
ROOT=Path(__file__).resolve().parents[1]
EXCLUDE_DIRS={'.git','.pytest_cache','__pycache__','.mypy_cache'}
EXCLUDE_SUFFIX={'.pyc','.pyo'}
def sha(p):
    h=hashlib.sha256(); h.update(Path(p).read_bytes()); return h.hexdigest()
def include(p):
    parts=set(p.parts)
    if parts & EXCLUDE_DIRS: return False
    if p.suffix in EXCLUDE_SUFFIX: return False
    if p.name.startswith('.DS_Store'): return False
    if p.name.endswith('.zip'): return False
    return p.is_file()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--package-root',default='.'); ap.add_argument('--out',default='reproducibility/stage5a2_manifest.json'); args=ap.parse_args()
    base=(ROOT/args.package_root).resolve(); files=[]
    for p in sorted(base.rglob('*')):
        if include(p): files.append({'path':str(p.relative_to(ROOT)),'sha256':sha(p),'bytes':p.stat().st_size})
    out=ROOT/args.out; out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({'stage':'stage5a2_estimator_convergence_repair_replication_gate','created_utc':datetime.datetime.now(datetime.UTC).isoformat(),'manifest_scope':'package-wide excluding caches/bytecode/zip files','files':files,'file_count':len(files),'claim_scope':'artifact and convergence/replication gate only; no publication claim'},indent=2))
    print(f'stage5a2 package-wide manifest wrote {out}; files={len(files)}')
if __name__=='__main__': main()
