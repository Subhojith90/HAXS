#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))
from build_stage5c2gR32A1_candidate import closure_paths, runtime_paths
from stage5c2gR32A1_authorization import ROOT, atomic_write_json, sha256_file, sha256_payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "results/stage5c2gR32A1/protocol/ROOT_MANIFEST.json",
    )
    args = parser.parse_args()
    if args.out.exists() or args.out.is_symlink():
        raise RuntimeError("refusing to overwrite root manifest")
    test_ledger = ROOT / "results/stage5c2gR32A1/protocol/NAMED_TEST_LEDGER.json"
    if not test_ledger.is_file() or test_ledger.is_symlink():
        raise RuntimeError("named-test ledger is required before root manifest")
    runtime = {
        path.relative_to(ROOT).as_posix(): sha256_file(path)
        for path in runtime_paths()
    }
    closure = {
        path.relative_to(ROOT).as_posix(): sha256_file(path)
        for path in closure_paths()
    }
    payload = {
        "schema_version": "haxs.stage5c2gR32A1.root-manifest.v1",
        "policy": "exact_self_contained_deny_by_default_v1",
        "external_root_reconstruction_forbidden": True,
        "allowed_top_level_entries": [
            "README.md",
            "STAGE3A_COMMANDS.sh",
            "STAGE3_COMMANDS.sh",
            "STAGE5C2GR32_COMMANDS.sh",
            "STAGE5C2GR3_COMMANDS.sh",
            "configs",
            "docs",
            "output",
            "pyproject.toml",
            "requirements-stage5c2gR2.lock",
            "requirements-stage5c2gR3.in",
            "requirements-stage5c2gR3.lock",
            "results",
            "scripts",
            "scripts_patch",
            "src",
            "tests",
        ],
        "forbidden_root_hooks": [
            "conftest.py",
            "sitecustomize.py",
            "usercustomize.py",
        ],
        "runtime_files": runtime,
        "closure_files": closure,
        "named_test_ledger": {
            "path": test_ledger.relative_to(ROOT).as_posix(),
            "sha256": sha256_file(test_ledger),
        },
    }
    payload["root_manifest_sha256"] = sha256_payload(payload)
    atomic_write_json(args.out, payload)
    print(
        json.dumps(
            {
                "status": "PASS",
                "root_manifest_sha256": payload["root_manifest_sha256"],
                "runtime_files": len(runtime),
                "closure_files": len(closure),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
