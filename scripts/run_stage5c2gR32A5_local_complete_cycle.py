#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from finalize_stage5c2gR32A5_authorization import (
    BLOCKED_SCOPES,
    _safe_extract,
    authorize,
    verify_complete_g0_return,
)
from launch_stage5c2gR32A5_G1_isolated import execute_once, load_authorization
from stage5c2gR32A5_common import load_candidate, sha256_file, sha256_payload

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--synthetic-g0-return", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    protocol = args.protocol.absolute()
    g0_return = args.synthetic_g0_return.absolute()
    out = args.out.absolute()
    if out.exists() or out.is_symlink():
        raise RuntimeError("refusing to overwrite A5 local complete lifecycle")
    out.mkdir(parents=True)
    candidate = load_candidate()
    protocol_sha = sha256_file(protocol)
    with tempfile.TemporaryDirectory(prefix="haxs-stage5c2gR32A5-cycle-return-") as directory:
        with zipfile.ZipFile(g0_return) as archive:
            prefix = _safe_extract(archive, Path(directory))
        comparison, return_sha = verify_complete_g0_return(
            Path(directory) / prefix, candidate, protocol_sha, allow_synthetic=True
        )
    contracts = candidate["authorization_contract"]
    receipt = {
        "schema_version": "haxs.stage5c2gR32A5.authorization.v1",
        "receipt_id": str(uuid.uuid4()),
        "decision": "ACCEPT_AND_AUTHORIZE_G1_ONLY",
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
        "authorized_scope": "G1_ONLY",
        "blocked_scopes": BLOCKED_SCOPES,
        "issued_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "issuer": {"name": "LOCAL_SYNTHETIC_ENGINEERING_FIXTURE", "role": "SUPERVISOR"},
    }
    receipt_path = out / "SYNTHETIC_RECEIPT_NOT_SUPERVISORY.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    control = out / "external_control_plane"
    authorize(
        receipt_path, protocol, g0_return, control,
        allow_synthetic=True,
    )
    authorization = load_authorization(control, candidate, ROOT)
    terminal = execute_once(
        candidate, authorization, control,
        lambda: (0, "A5_RUNNER_STUB_EXECUTED_EXACTLY_ONCE"), ROOT,
        root_verifier=lambda *_: {"status": "PASS", "immutable": True},
        environment_verifier=lambda *_args, **_kwargs: {"status": "PASS", "installed": True},
    )
    decision = {
        "schema_version": "haxs.stage5c2gR32A5.local-complete-lifecycle.v1",
        "status": "PASS",
        "candidate_sha256": candidate["candidate_sha256"],
        "protocol_archive_sha256": protocol_sha,
        "g0_return_sha256": return_sha,
        "two_host_g0_sha256": comparison["comparison_sha256"],
        "terminal_state_sha256": terminal["state_sha256"],
        "runner_stub_executed": True,
        "synthetic_dry_run": True,
        "receipt_eligible": False,
        "scientific_execution_performed": False,
        "decision_sha256": "",
    }
    decision["decision_sha256"] = sha256_payload(
        {key: value for key, value in decision.items() if key != "decision_sha256"}
    )
    (out / "LOCAL_COMPLETE_LIFECYCLE.json").write_text(
        json.dumps(decision, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(decision, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
