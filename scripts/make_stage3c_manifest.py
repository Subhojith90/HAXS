#!/usr/bin/env python
from __future__ import annotations
import argparse, hashlib, json, sys, platform
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def sha(p):
    h=hashlib.sha256();
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--results',default='results/stage3c_preflight'); ap.add_argument('--out',default='reproducibility/stage3c_preflight_manifest.json')
    args=ap.parse_args(); res=ROOT/args.results; out=ROOT/args.out; out.parent.mkdir(parents=True,exist_ok=True)
    files=[]
    for base in [res, ROOT/'figures/stage3c_preflight', ROOT/'manuscript/stage3c_preflight']:
        if base.exists():
            for p in sorted(base.rglob('*')):
                if p.is_file(): files.append({'path':str(p.relative_to(ROOT)),'sha256':sha(p),'bytes':p.stat().st_size})
    manifest={'stage':'stage3c_preflight','python':sys.version,'platform':platform.platform(),'file_count':len(files),'files':files,'commands':['python -m pip install -e .','python scripts/run_tests.py','pytest tests/stage2 tests/stage3 tests/stage3a tests/stage3b tests/stage3c tests/regression -q','python scripts/run_stage3c_preflight_all.py']}
    out.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(f'stage3c manifest wrote {out}; files={len(files)}')
if __name__=='__main__': main()
