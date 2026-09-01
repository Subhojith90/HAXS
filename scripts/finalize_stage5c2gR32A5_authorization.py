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

from stage5c2gR32A5_common import (
    commit_authorization_bundle,
    load_candidate,
    safe_relative,
    sha256_file,
    sha256_payload,
    strict_json,
)
from stage5c2gR32A5_g0 import finalize_comparison, recompute_two_host_g0

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
        if item.flag_bits & 0x1:
            raise RuntimeError(f"encrypted G0 return entry: {item.filename}")
        if not path.parts or path.is_absolute() or ".." in path.parts or stat.S_ISLNK(mode):
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
    allow_synthetic: bool = False,
) -> tuple[dict, str]:
    record = strict_json(return_root / "G0_RETURN.json")
    required = {
        "schema_version", "candidate_sha256", "protocol_archive_sha256",
        "protocol_content_sha256", "transport_container_sha256", "protocol_path",
        "host_a_path", "host_b_path", "comparison_path", "files",
        "scientific_execution_performed", "G1_authorized", "synthetic_dry_run",
        "return_sha256",
    }
    if set(record) != required:
        raise RuntimeError("complete R3.2A.5 G0 return schema failed")
    canonical = {key: value for key, value in record.items() if key != "return_sha256"}
    if (
        record["schema_version"] != "haxs.stage5c2gR32A5.complete-g0-return.v1"
        or record["return_sha256"] != sha256_payload(canonical)
        or record["candidate_sha256"] != candidate["candidate_sha256"]
        or record["protocol_archive_sha256"] != actual_protocol_sha256
        or record["protocol_content_sha256"] != candidate["protocol_content_sha256"]
        or record["scientific_execution_performed"] is not False
        or record["G1_authorized"] is not False
        or not isinstance(record["synthetic_dry_run"], bool)
        or (record["synthetic_dry_run"] is not False and not allow_synthetic)
    ):
        raise RuntimeError("complete G0 return identity, protocol, or scope failed")
    observed = {
        path.relative_to(return_root).as_posix(): sha256_file(path)
        for path in sorted(return_root.rglob("*"))
        if path.is_file() and path.name != "G0_RETURN.json"
    }
    if observed != record["files"]:
        raise RuntimeError("complete G0 return file manifest failed")
    if record["transport_container_sha256"] != sha256_payload(observed):
        raise RuntimeError("complete G0 return transport-container identity failed")
    returned_protocol = return_root / safe_relative(record["protocol_path"])
    if (
        not returned_protocol.is_file() or returned_protocol.is_symlink()
        or sha256_file(returned_protocol) != actual_protocol_sha256
    ):
        raise RuntimeError("complete G0 return embedded protocol identity failed")
    host_a = return_root / safe_relative(record["host_a_path"])
    host_b = return_root / safe_relative(record["host_b_path"])
    supplied = strict_json(return_root / safe_relative(record["comparison_path"]))
    recomputed = finalize_comparison(
        recompute_two_host_g0(host_a, host_b, return_root, candidate, actual_protocol_sha256)
    )
    if supplied != recomputed:
        raise RuntimeError("supplied comparator is stale, forged, or semantically invalid")
    return recomputed, record["return_sha256"]


def validate_receipt(
    receipt: dict, candidate: dict, protocol_sha256: str,
    return_sha256: str, comparison: dict,
) -> dict:
    if set(receipt) != RECEIPT_KEYS:
        raise RuntimeError("A5 receipt has missing or additional keys")
    try:
        uuid.UUID(str(receipt.get("receipt_id", "")))
        issued = datetime.fromisoformat(str(receipt.get("issued_at_utc", "")).replace("Z", "+00:00"))
    except ValueError as error:
        raise RuntimeError("A5 receipt UUID or timestamp failed") from error
    if issued.tzinfo is None or issued.utcoffset() != timezone.utc.utcoffset(issued):
        raise RuntimeError("A5 receipt timestamp must be UTC")
    if (
        receipt.get("schema_version") != "haxs.stage5c2gR32A5.authorization.v1"
        or receipt.get("decision") != "ACCEPT_AND_AUTHORIZE_G1_ONLY"
        or receipt.get("candidate_sha256") != candidate["candidate_sha256"]
        or receipt.get("protocol_archive_sha256") != protocol_sha256
        or receipt.get("authorized_scope") != "G1_ONLY"
        or receipt.get("blocked_scopes") != BLOCKED_SCOPES
        or not str(receipt.get("issued_at_utc", "")).endswith("Z")
        or set(receipt.get("issuer", {})) != {"name", "role"}
        or receipt["issuer"].get("role") != "SUPERVISOR"
        or not str(receipt["issuer"].get("name", "")).strip()
    ):
        raise RuntimeError("A5 receipt identity, decision, or scope failed")
    contracts = candidate["authorization_contract"]
    expected = {
        "runtime_tree_sha256": candidate["runtime_tree_sha256"],
        "wheel_sha256": candidate["wheel"]["sha256"],
        "environment_sha256": candidate["environment"]["sha256"],
        "g1_config_sha256": contracts["g1_config"]["sha256"],
        "g1_plan_sha256": contracts["g1_plan"]["sha256"],
        "unit_registry_sha256": contracts["unit_registry"]["sha256"],
        "runner_sha256": contracts["runner"]["sha256"],
        "test_ledger_sha256": contracts["test_ledger"]["sha256"],
        "g0_return_sha256": return_sha256,
        "two_host_g0_sha256": comparison["comparison_sha256"],
    }
    mismatches = [field for field, value in expected.items() if receipt[field] != value]
    if mismatches:
        raise RuntimeError(f"A5 receipt evidence mismatch: {mismatches}")
    return receipt


def authorize(
    receipt_path: Path, protocol: Path, g0_return: Path, control_root: Path,
    root: Path = ROOT, candidate: dict | None = None,
    protocol_verifier=None, return_verifier=None, allow_synthetic: bool = False,
) -> dict:
    candidate = candidate or load_candidate(root)
    if not protocol.is_file() or protocol.is_symlink() or protocol.suffix.lower() != ".zip":
        raise RuntimeError("official A5 protocol must be one safe ZIP")
    protocol_sha = sha256_file(protocol)
    if protocol_verifier is None:
        from verify_stage5c2gR32A5_fresh_unzip import verify_protocol
        protocol_verifier = verify_protocol
    verified = protocol_verifier(protocol)
    if (
        verified["candidate_sha256"] != candidate["candidate_sha256"]
        or verified["protocol_content_sha256"] != candidate["protocol_content_sha256"]
    ):
        raise RuntimeError("A5 protocol and candidate identity differ")
    if not g0_return.is_file() or g0_return.is_symlink() or g0_return.suffix.lower() != ".zip":
        raise RuntimeError("official complete A5 G0 return must be one safe ZIP")
    if return_verifier is None:
        with tempfile.TemporaryDirectory(prefix="haxs-stage5c2gR32A5-finalizer-") as directory:
            with zipfile.ZipFile(g0_return) as archive:
                prefix = _safe_extract(archive, Path(directory))
            comparison, return_sha = verify_complete_g0_return(
                Path(directory) / prefix, candidate, protocol_sha,
                allow_synthetic=allow_synthetic,
            )
    else:
        comparison, return_sha = return_verifier(g0_return, candidate, protocol_sha)
    receipt = validate_receipt(
        strict_json(receipt_path), candidate, protocol_sha, return_sha, comparison
    )
    authorization = {
        "schema_version": "haxs.stage5c2gR32A5.atomic-authorization.v1",
        "status": "LOCKED_G1_ONLY",
        "candidate_sha256": candidate["candidate_sha256"],
        "protocol_archive_sha256": protocol_sha,
        "g0_return_sha256": return_sha,
        "two_host_g0_sha256": comparison["comparison_sha256"],
        "receipt_id": receipt["receipt_id"],
        "official_attempt_limit": 1,
        "setup_preflight_required_before_attempt": True,
        "immutable_root_mutation_permitted": False,
        "receipt_sha256": "",
    }
    namespace = commit_authorization_bundle(
        control_root, candidate, receipt_path, authorization, root
    )
    committed = strict_json(namespace / "AUTHORIZATION.json")
    return committed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--protocol-archive", type=Path, required=True)
    parser.add_argument("--g0-return", type=Path, required=True)
    parser.add_argument("--control-root", type=Path, required=True)
    parser.add_argument("--commit", action="store_true", required=True)
    args = parser.parse_args()
    result = authorize(
        args.receipt.absolute(), args.protocol_archive.absolute(),
        args.g0_return.absolute(), args.control_root.absolute()
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
