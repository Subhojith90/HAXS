#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2gR2_common import assert_protocol_locked
from stage5c2gR2_state import verify_gate_state


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--gate", choices=["G1"], required=True); args = parser.parse_args()
    lock = assert_protocol_locked(); state = verify_gate_state(args.gate, lock)
    print(json.dumps({"gate": args.gate, "status": "VERIFIED_PASS", "attempt_id": state["attempt_id"], "state_sha256": state["state_sha256"], "manifest_sha256": state["manifest_sha256"]}, indent=2))


if __name__ == "__main__": main()

