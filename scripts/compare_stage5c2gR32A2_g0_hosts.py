#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2gR32A2_common import atomic_write_json, load_candidate
from stage5c2gR32A2_g0 import finalize_comparison, recompute_two_host_g0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host-a", type=Path, required=True)
    parser.add_argument("--host-b", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists() or args.out.is_symlink():
        raise RuntimeError("refusing to overwrite authoritative two-host comparison")
    candidate = load_candidate()
    payload = finalize_comparison(
        recompute_two_host_g0(
            args.host_a.resolve(), args.host_b.resolve(), args.evidence_root.resolve(), candidate
        )
    )
    atomic_write_json(args.out, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
