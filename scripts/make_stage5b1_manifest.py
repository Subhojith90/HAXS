#!/usr/bin/env python
from __future__ import annotations
import argparse, datetime, hashlib, json
from pathlib import Path

def digest(p: Path):
    h=hashlib.sha256(); h.update(p.read_bytes()); return h.hexdigest()

def build_manifest(root: Path, stage: str):
    files=[]
    for p in sorted(root.rglob('*')):
        if p.is_file() and not any(part in {'.git','__pycache__','.pytest_cache'} for part in p.parts):
            files.append({'path':str(p.relative_to(root)),'sha256':digest(p),'bytes':p.stat().st_size})
    return {'stage':stage,'created_utc':datetime.datetime.now(datetime.UTC).isoformat(),'root':str(root),'file_count':len(files),'files':files}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--package-root',default='.'); ap.add_argument('--result-root',default='results/stage5b1_lite'); ap.add_argument('--out-dir',default='reproducibility'); args=ap.parse_args()
    out=Path(args.out_dir); out.mkdir(parents=True,exist_ok=True)
    source=build_manifest(Path(args.package_root),'stage5b1_source_manifest')
    result=build_manifest(Path(args.result_root),'stage5b1_result_manifest')
    (out/'stage5b1_source_manifest.json').write_text(json.dumps(source,indent=2))
    (out/'stage5b1_result_manifest.json').write_text(json.dumps(result,indent=2))
    print('stage5b1 manifests wrote', out, 'source_files=',source['file_count'],'result_files=',result['file_count'])
if __name__=='__main__': main()
