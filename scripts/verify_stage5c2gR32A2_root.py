#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2gR32A2_common import (
    ROOT_MANIFEST_PATH,
    assert_exact_membership,
    assert_no_forbidden_import_artifacts,
    load_candidate,
    safe_relative,
    sha256_file,
    sha256_payload,
    strict_json,
    tree_snapshot,
)


def parse_bundle_ledger(root: Path) -> dict[str, str]:
    ledger = root / "BUNDLE_CONTENTS_SHA256.txt"
    if not ledger.is_file() or ledger.is_symlink():
        raise RuntimeError("exact execution root requires BUNDLE_CONTENTS_SHA256.txt")
    expected: dict[str, str] = {}
    for line in ledger.read_text(encoding="utf-8").splitlines():
        if not line or "  " not in line:
            raise RuntimeError("malformed bundle checksum ledger")
        digest, relative_text = line.split("  ", 1)
        relative = safe_relative(relative_text).as_posix()
        if relative in expected or relative == "BUNDLE_CONTENTS_SHA256.txt":
            raise RuntimeError("duplicate or self-referential bundle ledger entry")
        expected[relative] = digest
    return expected


def verify_root(root: Path, candidate: dict | None = None) -> dict:
    candidate = candidate or load_candidate(root)
    manifest_path = root / ROOT_MANIFEST_PATH.relative_to(ROOT)
    manifest = strict_json(manifest_path)
    canonical = {key: value for key, value in manifest.items() if key != "root_manifest_sha256"}
    if (
        manifest.get("schema_version") != "haxs.stage5c2gR32A2.root-manifest.v1"
        or manifest.get("policy") != "whole_root_deny_by_default_v2"
        or manifest.get("root_manifest_sha256") != sha256_payload(canonical)
        or sha256_file(manifest_path)
        != candidate["authorization_contract"]["root_manifest"]["sha256"]
    ):
        raise RuntimeError("candidate-bound exact root manifest failed")
    expected_bundle = parse_bundle_ledger(root)
    actual, directories = tree_snapshot(root)
    bundle_digest = actual.pop("BUNDLE_CONTENTS_SHA256.txt", None)
    if bundle_digest is None:
        raise RuntimeError("whole-root bundle ledger is missing")
    assert_exact_membership(actual, expected_bundle, "whole-root file")
    expected_directories = sorted(
        {
            parent.as_posix()
            for relative in expected_bundle
            for parent in safe_relative(relative).parents
            if parent != Path(".")
        }
    )
    if sorted(directories) != expected_directories:
        raise RuntimeError(
            "whole-root directory identity failed: "
            f"extra={sorted(set(directories)-set(expected_directories))[:8]} "
            f"missing={sorted(set(expected_directories)-set(directories))[:8]}"
        )
    expected_runtime = manifest["runtime_files"]
    runtime_actual = {name: actual.get(name) for name in expected_runtime}
    if runtime_actual != expected_runtime:
        raise RuntimeError("candidate runtime subset differs from exact root manifest")
    if not set(manifest["runtime_directories"]).issubset(directories):
        raise RuntimeError("runtime directory identity failed")
    assert_no_forbidden_import_artifacts(actual)
    return {
        "stage": "stage5c2gR32A2_root",
        "status": "PASS",
        "candidate_sha256": candidate["candidate_sha256"],
        "files": len(actual),
        "directories": len(directories),
        "bundle_ledger_sha256": bundle_digest,
        "root_manifest_sha256": manifest["root_manifest_sha256"],
        "bytecode_closed": True,
        "whole_root_exact": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    print(json.dumps(verify_root(args.root.resolve()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
