#!/usr/bin/env python
from __future__ import annotations
import argparse, hashlib, json, datetime, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from haxs.io.result_store import ensure_dir, save_json

def sha(p):
    h=hashlib.sha256(); h.update(p.read_bytes()); return h.hexdigest()

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--results',default='results/stage4b_lite'); ap.add_argument('--out',default='reproducibility/stage4b_manifest.json')
    args=ap.parse_args(); base=ROOT/args.results; out=ROOT/args.out; ensure_dir(out.parent)
    files=[]
    for p in sorted(base.rglob('*')):
        if p.is_file(): files.append({'path':str(p.relative_to(ROOT)),'sha256':sha(p),'bytes':p.stat().st_size})
    save_json(out,{'stage':'stage4b_targeted_mechanism_checkpoint','created_utc':datetime.datetime.now(datetime.UTC).isoformat(),'files':files,'file_count':len(files),'note':'fresh manifest for Stage 4B checkpoint outputs only; excludes caches and stale outputs'})
    print(f'stage4b manifest wrote {out}; files={len(files)}')
if __name__=='__main__': main()
