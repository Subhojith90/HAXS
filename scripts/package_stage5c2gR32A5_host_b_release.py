#!/usr/bin/env python
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from prepare_stage5c2gR32A5_github_release import main


if __name__ == "__main__":
    main()
