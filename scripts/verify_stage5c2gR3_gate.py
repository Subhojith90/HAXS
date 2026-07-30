#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2gR3_common import assert_protocol_locked
from stage5c2gR3_state import verify_gate_state


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--gate", choices=["G1"], required=True); parser.add_argument("--semantic-recompute", action="store_true", required=True); args = parser.parse_args()
    state = verify_gate_state(args.gate, assert_protocol_locked())
    print(json.dumps({"gate": args.gate, "status": "PASS", "semantic_recompute": True, "state_sha256": state["state_sha256"]}, indent=2))


if __name__ == "__main__": main()
