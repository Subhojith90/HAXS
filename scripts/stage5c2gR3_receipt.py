from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from pathlib import Path

from stage5c2gR3_common import sha256_file

SCHEMA_VERSION = "haxs.stage5c2gR3.1.authorization.v1"
DECISION = "ACCEPT_AND_AUTHORIZE_G1_ONLY"
AUTHORIZED_SCOPE = "G1_ONLY"
BLOCKED_SCOPES = ["G2", "G3", "G4", "STAGE5C3", "STAGE5D", "MANUSCRIPT_RESULT_CLAIMS", "EXACT_MOBILE_HOLE_CLAIMS", "PUBLIC_RELEASE"]
TOP_LEVEL_KEYS = {"schema_version", "receipt_id", "decision", "candidate_sha256", "protocol_archive_sha256", "runtime_tree_sha256", "authorized_scope", "blocked_scopes", "issued_at_utc", "issuer"}
ISSUER_KEYS = {"name", "role"}


def _sha256(value: object, field: str) -> str:
    text = str(value)
    if not re.fullmatch(r"[0-9a-f]{64}", text):
        raise RuntimeError(f"structured receipt {field} is not a lowercase SHA-256")
    return text


def load_and_validate_receipt(path: str | Path, candidate: dict, protocol_archive: str | Path) -> dict:
    receipt_path = Path(path)
    if not receipt_path.is_file() or receipt_path.is_symlink():
        raise RuntimeError("structured supervisor receipt is missing or unsafe")
    try:
        payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise RuntimeError("supervisor receipt must be strict JSON") from error
    if not isinstance(payload, dict) or set(payload) != TOP_LEVEL_KEYS:
        raise RuntimeError("structured receipt top-level schema differs from the exact authorization schema")
    if payload["schema_version"] != SCHEMA_VERSION or payload["decision"] != DECISION or payload["authorized_scope"] != AUTHORIZED_SCOPE:
        raise RuntimeError("structured receipt decision or scope is not exact G1-only authorization")
    if payload["blocked_scopes"] != BLOCKED_SCOPES:
        raise RuntimeError("structured receipt does not preserve every downstream block")
    try:
        uuid.UUID(str(payload["receipt_id"]))
    except (ValueError, AttributeError) as error:
        raise RuntimeError("structured receipt ID must be a UUID") from error
    issuer = payload["issuer"]
    if not isinstance(issuer, dict) or set(issuer) != ISSUER_KEYS or issuer.get("role") != "SUPERVISOR" or not str(issuer.get("name", "")).strip():
        raise RuntimeError("structured receipt issuer schema failed")
    try:
        issued = datetime.fromisoformat(str(payload["issued_at_utc"]).replace("Z", "+00:00"))
    except ValueError as error:
        raise RuntimeError("structured receipt issuance time is not ISO-8601") from error
    if issued.tzinfo is None or issued.utcoffset() is None or issued.utcoffset().total_seconds() != 0:
        raise RuntimeError("structured receipt issuance time must be explicitly UTC")
    archive_path = Path(protocol_archive)
    if not archive_path.is_file() or archive_path.is_symlink():
        raise RuntimeError("receipt-bound protocol archive is missing or unsafe")
    candidate_sha = _sha256(candidate.get("candidate_sha256"), "candidate_sha256")
    runtime_sha = _sha256(candidate.get("runtime_tree_sha256"), "runtime_tree_sha256")
    if _sha256(payload["candidate_sha256"], "candidate_sha256") != candidate_sha:
        raise RuntimeError("structured receipt candidate identity failed")
    if _sha256(payload["runtime_tree_sha256"], "runtime_tree_sha256") != runtime_sha:
        raise RuntimeError("structured receipt runtime-tree identity failed")
    if _sha256(payload["protocol_archive_sha256"], "protocol_archive_sha256") != sha256_file(archive_path):
        raise RuntimeError("structured receipt protocol-archive identity failed")
    return payload
