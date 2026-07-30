
#!/usr/bin/env python
from __future__ import annotations
import argparse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from haxs.io.hashes import write_sha256_listing

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root',default='.'); ap.add_argument('--out',default='MANIFEST.sha256')
    a=ap.parse_args(); root=Path(a.root).resolve(); out=Path(a.out); out = out if out.is_absolute() else root/out
    write_sha256_listing(root, out)
    print({'stage':'stage5c2d_manifest','root':str(root),'manifest':str(out)})
if __name__=='__main__': main()
