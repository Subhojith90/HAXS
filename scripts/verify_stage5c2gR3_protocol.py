#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2gR3_common import build_candidate, require_isolated_interpreter, sha256_payload
from stage5c2gR3_state import atomic_write_json


def main() -> None:
    require_isolated_interpreter(ROOT)
    parser = argparse.ArgumentParser(); parser.add_argument("--custody-root", required=True); args = parser.parse_args()
    payload = build_candidate(ROOT, args.custody_root)
    candidate_sha = sha256_payload(payload)
    path = ROOT / "results/stage5c2gR3/protocol/CANDIDATE.json"
    atomic_write_json(path, {**payload, "candidate_sha256": candidate_sha})
    print(json.dumps({"status": "AWAITING_SUPERVISORY_ACCEPTANCE_BEFORE_STRUCTURED_RECEIPT", "candidate_sha256": candidate_sha, "runtime_files": len(payload["runtime_tree"]["files"]), "runtime_directories": len(payload["runtime_tree"]["directories"]), "config_hashes": payload["canonical_configs"], "plan_hashes": payload["expected_plans"], "environment_attestation_sha256": sha256_payload(payload["environment"]["observed"])}, indent=2))


if __name__ == "__main__": main()
