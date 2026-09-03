#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_stage5c2gR32A4_candidate import closure_paths, runtime_paths
from stage5c2gR32A4_common import atomic_write_json, sha256_file, sha256_payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "results/stage5c2gR32A4/protocol/ROOT_MANIFEST.json")
    args = parser.parse_args()
    if args.out.exists() or args.out.is_symlink():
        raise RuntimeError("refusing to overwrite R3.2A.4 root manifest")
    ledger = ROOT / "results/stage5c2gR32A4/protocol/NAMED_TEST_LEDGER.json"
    paths = runtime_paths()
    runtime = {path.relative_to(ROOT).as_posix(): sha256_file(path) for path in paths}
    directories = sorted({
        parent.relative_to(ROOT).as_posix() for path in paths for parent in path.parents
        if parent != ROOT and parent.is_relative_to(ROOT)
    })
    closure = {path.relative_to(ROOT).as_posix(): sha256_file(path) for path in closure_paths()}
    payload = {
        "schema_version": "haxs.stage5c2gR32A4.root-manifest.v1",
        "policy": "whole_root_deny_by_default_v3_semantic_evidence_bound",
        "runtime_files": runtime, "runtime_directories": directories,
        "closure_files": closure,
        "named_test_ledger": {"path": ledger.relative_to(ROOT).as_posix(), "sha256": sha256_file(ledger)},
        "all_unlisted_files_and_directories_rejected": True,
        "forbidden_import_channels": ["__pycache__", ".pyc", ".pyo", ".pth", "symlink", "external_PYTHONPATH", "root_hooks"],
    }
    payload["root_manifest_sha256"] = sha256_payload(payload)
    atomic_write_json(args.out, payload)
    print(json.dumps({"status": "PASS", "root_manifest_sha256": payload["root_manifest_sha256"], "runtime_files": len(runtime)}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
