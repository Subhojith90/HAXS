#!/usr/bin/env python
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from stage5c2gR32A2_common import (
    assert_exact_membership,
    assert_no_forbidden_import_artifacts,
    safe_relative,
    sha256_file,
    sha256_payload,
    strict_json,
    tree_snapshot,
)
from stage5c2gR32A5_common import load_candidate

MANIFEST = Path("results/stage5c2gR32A5/protocol/IMMUTABLE_ROOT_MANIFEST.json")


def verify_root(root: Path, candidate: dict | None = None) -> dict:
    candidate = candidate or load_candidate(root)
    manifest_path = root / MANIFEST
    manifest = strict_json(manifest_path)
    canonical = {key: value for key, value in manifest.items() if key != "root_manifest_sha256"}
    if (
        manifest.get("schema_version") != "haxs.stage5c2gR32A5.immutable-root.v1"
        or manifest.get("policy") != "immutable_whole_root_deny_by_default_v1"
        or manifest.get("root_manifest_sha256") != sha256_payload(canonical)
        or sha256_file(manifest_path) != candidate["authorization_contract"]["root_manifest"]["sha256"]
    ):
        raise RuntimeError("candidate-bound A5 immutable-root manifest failed")
    ledger_path = root / "BUNDLE_CONTENTS_SHA256.txt"
    expected = {}
    for line in ledger_path.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        relative = safe_relative(relative).as_posix()
        if relative in expected or relative == "BUNDLE_CONTENTS_SHA256.txt":
            raise RuntimeError("duplicate or self-referential immutable-root ledger entry")
        expected[relative] = digest
    actual, directories = tree_snapshot(root)
    ledger_sha = actual.pop("BUNDLE_CONTENTS_SHA256.txt", None)
    assert_exact_membership(actual, expected, "immutable whole-root file")
    expected_directories = sorted({
        parent.as_posix() for relative in expected
        for parent in safe_relative(relative).parents if parent != Path(".")
    })
    if sorted(directories) != expected_directories:
        raise RuntimeError("immutable whole-root directory identity failed")
    assert_no_forbidden_import_artifacts(actual)
    return {
        "stage": "stage5c2gR32A5_immutable_root", "status": "PASS",
        "candidate_sha256": candidate["candidate_sha256"],
        "files": len(actual), "directories": len(directories),
        "bundle_ledger_sha256": ledger_sha,
        "root_manifest_sha256": manifest["root_manifest_sha256"],
        "bytecode_closed": True, "whole_root_exact": True,
    }


if __name__ == "__main__":
    print(json.dumps(verify_root(Path.cwd()), indent=2, sort_keys=True))
