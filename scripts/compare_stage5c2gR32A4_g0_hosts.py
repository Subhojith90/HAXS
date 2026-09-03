#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from stage5c2gR32A4_common import atomic_write_json, load_candidate, sha256_file
from stage5c2gR32A4_g0 import finalize_comparison, recompute_two_host_g0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host-a", type=Path, required=True)
    parser.add_argument("--host-b", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists() or args.out.is_symlink():
        raise RuntimeError("refusing to overwrite R3.2A.4 comparison")
    result = finalize_comparison(recompute_two_host_g0(
        args.host_a.absolute(), args.host_b.absolute(), args.evidence_root.absolute(),
        load_candidate(), sha256_file(args.protocol.absolute()),
    ))
    atomic_write_json(args.out, result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
