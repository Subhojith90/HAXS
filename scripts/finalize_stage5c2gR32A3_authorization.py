#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import stat
import sys
import tempfile
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2gR32A3_common import (
    AUTHORIZATION_PATH, LOCK_PATH, RECEIPT_PATH, STATE_PATH,
    exclusive_write_json, load_candidate, safe_relative, sha256_file, sha256_payload, strict_json,
)
from stage5c2gR32A3_g0 import finalize_comparison, recompute_two_host_g0

BLOCKED_SCOPES = [
    "G2", "G3", "G4", "STAGE5C3", "STAGE5D", "MANUSCRIPT_RESULT_CLAIMS",
    "EXACT_MOBILE_HOLE_CLAIMS", "PUBLIC_RELEASE",
]
RECEIPT_KEYS = {
    "schema_version", "receipt_id", "decision", "candidate_sha256",
    "protocol_archive_sha256", "runtime_tree_sha256", "wheel_sha256",
    "environment_sha256", "g1_config_sha256", "g1_plan_sha256",
    "unit_registry_sha256", "runner_sha256", "test_ledger_sha256",
    "g0_return_sha256", "two_host_g0_sha256", "authorized_scope",
    "blocked_scopes", "issued_at_utc", "issuer",
}


def _safe_extract(archive: zipfile.ZipFile, destination: Path) -> str:
    names = archive.namelist()
    if not names or len(names) != len(set(names)):
        raise RuntimeError("G0 return has duplicate or no entries")
    prefixes = set()
    for item in archive.infolist():
        path = PurePosixPath(item.filename)
        mode = item.external_attr >> 16
        if path.is_absolute() or ".." in path.parts or stat.S_ISLNK(mode):
            raise RuntimeError(f"unsafe G0 return entry: {item.filename}")
        if "__pycache__" in path.parts or path.suffix.lower() in {".pyc", ".pyo", ".pth"}:
            raise RuntimeError(f"forbidden import artifact: {item.filename}")
        prefixes.add(path.parts[0])
    if len(prefixes) != 1:
        raise RuntimeError("G0 return must have one canonical prefix")
    archive.extractall(destination)
    return prefixes.pop()


def verify_complete_g0_return(
    return_root: Path, candidate: dict, actual_protocol_sha256: str,
) -> tuple[dict, str]:
    record = strict_json(return_root / "G0_RETURN.json")
    required = {
        "schema_version", "candidate_sha256", "protocol_archive_sha256",
        "protocol_content_sha256", "transport_container_sha256", "host_a_path",
        "host_b_path", "comparison_path", "files", "scientific_execution_performed",
        "G1_authorized", "return_sha256",
    }
    if set(record) != required:
        raise RuntimeError("complete R3.2A.3 G0 return schema failed")
    canonical = {key: value for key, value in record.items() if key != "return_sha256"}
    if (
        record["schema_version"] != "haxs.stage5c2gR32A3.complete-g0-return.v1"
        or record["return_sha256"] != sha256_payload(canonical)
        or record["candidate_sha256"] != candidate["candidate_sha256"]
        or record["protocol_archive_sha256"] != actual_protocol_sha256
        or record["protocol_content_sha256"] != candidate["protocol_content_sha256"]
        or record["scientific_execution_performed"] is not False
        or record["G1_authorized"] is not False
    ):
        raise RuntimeError("complete G0 return identity, protocol, or scope failed")
    observed = {
        path.relative_to(return_root).as_posix(): sha256_file(path)
        for path in sorted(return_root.rglob("*"))
        if path.is_file() and path.name != "G0_RETURN.json"
    }
    if observed != record["files"]:
        raise RuntimeError("complete G0 return file manifest failed")
    host_a = return_root / safe_relative(record["host_a_path"])
    host_b = return_root / safe_relative(record["host_b_path"])
    supplied = strict_json(return_root / safe_relative(record["comparison_path"]))
    recomputed = finalize_comparison(
        recompute_two_host_g0(
            host_a, host_b, return_root, candidate, actual_protocol_sha256
        )
    )
    if supplied != recomputed:
        raise RuntimeError("supplied comparator is stale, forged, or semantically invalid")
    return recomputed, record["return_sha256"]


def validate_receipt(
    receipt: dict, candidate: dict, protocol_sha: str, return_sha: str, comparison: dict,
) -> dict:
    if set(receipt) != RECEIPT_KEYS:
        raise RuntimeError("structured receipt has missing or additional keys")
    if (
        receipt["schema_version"] != "haxs.stage5c2gR32A3.authorization.v1"
        or receipt["decision"] != "ACCEPT_AND_AUTHORIZE_G1_ONLY"
        or receipt["authorized_scope"] != "G1_ONLY"
        or receipt["blocked_scopes"] != BLOCKED_SCOPES
    ):
        raise RuntimeError("receipt schema, decision, or scope failed")
    try:
        uuid.UUID(str(receipt["receipt_id"]))
        issued = datetime.fromisoformat(str(receipt["issued_at_utc"]).replace("Z", "+00:00"))
    except ValueError as error:
        raise RuntimeError("receipt UUID or timestamp failed") from error
    if issued.tzinfo is None or issued.utcoffset() != timezone.utc.utcoffset(issued):
        raise RuntimeError("receipt timestamp must be UTC")
    if set(receipt["issuer"]) != {"name", "role"} or receipt["issuer"]["role"] != "SUPERVISOR" or not str(receipt["issuer"]["name"]).strip():
        raise RuntimeError("receipt issuer schema failed")
    contracts = candidate["authorization_contract"]
    expected = {
        "candidate_sha256": candidate["candidate_sha256"],
        "protocol_archive_sha256": protocol_sha,
        "runtime_tree_sha256": candidate["runtime_tree_sha256"],
        "wheel_sha256": candidate["wheel"]["sha256"],
        "environment_sha256": candidate["environment"]["sha256"],
        "g1_config_sha256": contracts["g1_config"]["sha256"],
        "g1_plan_sha256": contracts["g1_plan"]["sha256"],
        "unit_registry_sha256": contracts["unit_registry"]["sha256"],
        "runner_sha256": contracts["runner"]["sha256"],
        "test_ledger_sha256": contracts["test_ledger"]["sha256"],
        "g0_return_sha256": return_sha,
        "two_host_g0_sha256": comparison["comparison_sha256"],
    }
    mismatches = [field for field, value in expected.items() if receipt[field] != value]
    if mismatches:
        raise RuntimeError(f"receipt identity mismatch: {mismatches}")
    return receipt


def authorize(
    receipt_path: Path, protocol: Path, g0_return: Path, dry_run: bool,
    root: Path = ROOT, protocol_verifier=None,
) -> dict:
    forbidden = [root / path.relative_to(ROOT) for path in [AUTHORIZATION_PATH, LOCK_PATH, RECEIPT_PATH, STATE_PATH]]
    if any(path.exists() or path.is_symlink() for path in forbidden):
        raise RuntimeError("authorization/state object already exists")
    candidate = load_candidate(root)
    if candidate["execution_permissions"]["G1"] != "BLOCKED_PENDING_NEW_SUPERVISORY_REVIEW_AND_RECEIPT":
        raise RuntimeError("candidate is not fail-closed before review")
    protocol_sha = sha256_file(protocol)
    if protocol_verifier is None:
        from verify_stage5c2gR32A3_fresh_unzip import verify_protocol
        protocol_verifier = verify_protocol
    verified = protocol_verifier(protocol)
    if verified["candidate_sha256"] != candidate["candidate_sha256"]:
        raise RuntimeError("protocol and authorization candidate differ")
    if verified["protocol_content_sha256"] != candidate["protocol_content_sha256"]:
        raise RuntimeError("protocol semantic/content identity differs")
    with tempfile.TemporaryDirectory(prefix="haxs-stage5c2gR32A3-finalizer-") as directory:
        if g0_return.is_dir() and not g0_return.is_symlink():
            return_root = g0_return.resolve()
        else:
            if not g0_return.is_file() or g0_return.is_symlink():
                raise RuntimeError("complete G0 return is missing or unsafe")
            with zipfile.ZipFile(g0_return) as archive:
                prefix = _safe_extract(archive, Path(directory))
            return_root = Path(directory) / prefix
        comparison, return_sha = verify_complete_g0_return(
            return_root, candidate, protocol_sha
        )
        receipt = validate_receipt(
            strict_json(receipt_path), candidate, protocol_sha, return_sha, comparison
        )
    payload = {
        "schema_version": "haxs.stage5c2gR32A3.atomic-authorization.v1",
        "status": "VALIDATED_DRY_RUN" if dry_run else "LOCKED_G1_ONLY",
        "candidate_sha256": candidate["candidate_sha256"],
        "actual_protocol_archive_sha256": protocol_sha,
        "receipt": receipt,
        "recomputed_two_host_g0": comparison,
        "official_attempt_limit": 1,
        "setup_preflight_required_before_attempt": True,
    }
    payload["authorization_sha256"] = sha256_payload(payload)
    if not dry_run:
        exclusive_write_json(root / AUTHORIZATION_PATH.relative_to(ROOT), payload)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--protocol-archive", type=Path, required=True)
    parser.add_argument("--g0-return", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--commit", action="store_true")
    args = parser.parse_args()
    result = authorize(
        args.receipt.resolve(), args.protocol_archive.resolve(),
        args.g0_return.resolve(), args.dry_run,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
