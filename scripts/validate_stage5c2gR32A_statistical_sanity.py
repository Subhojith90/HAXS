#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2gR32A_calibration import run_validation


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "configs/stage5c2gR32A/s03_validation.yaml")
    parser.add_argument("--out", type=Path, default=ROOT / "output/stage5c2gR32A/s03_validation")
    args = parser.parse_args()
    result = run_validation(args.config, args.out)
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
