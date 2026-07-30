#!/usr/bin/env python
from __future__ import annotations
import argparse, hashlib, json, sys, datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from haxs.io.result_store import ensure_dir, save_json

def sha(p):
    h=hashlib.sha256(); h.update(Path(p).read_bytes()); return h.hexdigest()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--results',default='results/stage4a_lite'); ap.add_argument('--out',default='reproducibility/stage4a_manifest.json')
    args=ap.parse_args(); r=ROOT/args.results; files=[]
    for p in sorted(r.rglob('*')):
        if p.is_file(): files.append({'path':str(p.relative_to(ROOT)),'sha256':sha(p),'bytes':p.stat().st_size})
    out=ROOT/args.out; out.parent.mkdir(parents=True,exist_ok=True)
    save_json(out,{'stage':'stage4a_mechanism_stability_diagnosis','created_utc':datetime.datetime.utcnow().isoformat()+'Z','files':files,'file_count':len(files),'note':'fresh manifest for Stage 4A diagnostic outputs only'})
    print(f'stage4a manifest wrote {out}; files={len(files)}')
if __name__=='__main__': main()
