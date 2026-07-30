#!/usr/bin/env python
from __future__ import annotations
import argparse, hashlib, json, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):
    h=hashlib.sha256(); h.update(Path(p).read_bytes()); return h.hexdigest()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--results',default='results/stage4_lite'); ap.add_argument('--out',default='reproducibility/stage4_manifest.json')
    args=ap.parse_args(); base=ROOT/args.results; files=[]
    for p in sorted(base.rglob('*')):
        if p.is_file(): files.append({'path':str(p.relative_to(ROOT)),'sha256':sha(p),'bytes':p.stat().st_size})
    out=ROOT/args.out; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps({'stage':'stage4','created_unix':time.time(),'file_count':len(files),'files':files},indent=2))
    print(f'stage4 manifest wrote {out}; files={len(files)}')
if __name__=='__main__': main()
