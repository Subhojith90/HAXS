#!/usr/bin/env python
from __future__ import annotations
import argparse, hashlib, datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def sha(p):
    h=hashlib.sha256(); h.update(p.read_bytes()); return h.hexdigest()

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--results',default='results/stage4d_lite'); ap.add_argument('--out',default='reproducibility/stage4d_manifest.json')
    args=ap.parse_args(); base=ROOT/args.results; out=ROOT/args.out; out.parent.mkdir(parents=True,exist_ok=True)
    import json
    files=[]
    for sub in [base, ROOT/'figures/stage4d_lite', ROOT/'manuscript/stage4d_lite']:
        if sub.exists():
            for p in sorted(sub.rglob('*')):
                if p.is_file(): files.append({'path':str(p.relative_to(ROOT)),'sha256':sha(p),'bytes':p.stat().st_size})
    out.write_text(json.dumps({'stage':'stage4d_targeted_publication_pilot','created_utc':datetime.datetime.now(datetime.UTC).isoformat(),'files':files,'file_count':len(files)},indent=2))
    print(f'stage4d manifest wrote {out}; files={len(files)}')
if __name__=='__main__': main()
