from __future__ import annotations

import json
import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from finalize_stage5c2gR32A5_authorization import BLOCKED_SCOPES, authorize as production_authorize
from launch_stage5c2gR32A5_G1_isolated import execute_once, load_authorization
from stage5c2gR32A2_common import sha256_file, sha256_payload
from stage5c2gR32A5_common import (
    AUTHORIZATION_NAME,
    RECEIPT_NAME,
    STATE_NAME,
    candidate_control_root,
    verify_control_root,
)


def candidate(immutable: Path) -> dict:
    contract_paths = {
        "launcher": "scripts/launch.py",
        "runner": "scripts/runner.py",
        "g1_config": "configs/g1.yaml",
        "g1_plan": "plans/g1.csv",
        "unit_registry": "plans/units.csv",
        "test_ledger": "results/ledger.json",
    }
    for name, relative in contract_paths.items():
        path = immutable / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"frozen {name}\n", encoding="utf-8")
    payload = {
        "schema_version": "haxs.stage5c2gR32A5.candidate.v1",
        "stage": "stage5c2gR32A5",
        "protocol_archive_sha256": "",
        "protocol_content_sha256": "frozen-protocol-content",
        "runtime_tree_sha256": "1" * 64,
        "wheel": {"path": "haxs.whl", "sha256": "2" * 64},
        "environment": {"path": "environment.json", "sha256": "3" * 64},
        "authorization_contract": {
            name: {"path": relative, "sha256": sha256_file(immutable / relative)}
            for name, relative in contract_paths.items()
        },
        "execution_permissions": {"G1": "BLOCKED_PENDING_NEW_SUPERVISORY_REVIEW_AND_RECEIPT"},
    }
    payload["candidate_sha256"] = sha256_payload(payload)
    return payload


def fixture(tmp_path: Path) -> tuple[Path, Path, Path, dict, Path]:
    immutable = tmp_path / "immutable protocol root"
    immutable.mkdir()
    protocol = tmp_path / "protocol.zip"
    protocol.write_bytes(b"frozen A5 protocol fixture")
    g0_return = tmp_path / "complete-g0-return.zip"
    g0_return.write_bytes(b"synthetic complete G0 fixture")
    control = tmp_path / "mutable control plane"
    item = candidate(immutable)
    item["protocol_archive_sha256"] = sha256_file(protocol)
    item["candidate_sha256"] = sha256_payload({key: value for key, value in item.items() if key != "candidate_sha256"})
    receipt = tmp_path / "receipt.json"
    receipt.write_text(json.dumps({
        "schema_version": "haxs.stage5c2gR32A5.authorization.v1",
        "receipt_id": "f320dc29-2b28-4890-bd55-b26a457cf24b",
        "decision": "ACCEPT_AND_AUTHORIZE_G1_ONLY",
        "candidate_sha256": item["candidate_sha256"],
        "protocol_archive_sha256": item["protocol_archive_sha256"],
        "runtime_tree_sha256": item["runtime_tree_sha256"],
        "wheel_sha256": item["wheel"]["sha256"],
        "environment_sha256": item["environment"]["sha256"],
        "g1_config_sha256": item["authorization_contract"]["g1_config"]["sha256"],
        "g1_plan_sha256": item["authorization_contract"]["g1_plan"]["sha256"],
        "unit_registry_sha256": item["authorization_contract"]["unit_registry"]["sha256"],
        "runner_sha256": item["authorization_contract"]["runner"]["sha256"],
        "test_ledger_sha256": item["authorization_contract"]["test_ledger"]["sha256"],
        "g0_return_sha256": "4" * 64,
        "two_host_g0_sha256": "5" * 64,
        "authorized_scope": "G1_ONLY",
        "blocked_scopes": BLOCKED_SCOPES,
        "issued_at_utc": "2026-09-01T00:00:00Z",
        "issuer": {"name": "Srinjoy", "role": "SUPERVISOR"},
    }, sort_keys=True) + "\n", encoding="utf-8")
    return immutable, protocol, control, item, receipt, g0_return


def commit_fixture_authorization(
    receipt: Path, protocol: Path, g0_return: Path, control: Path,
    immutable: Path, item: dict,
) -> dict:
    return production_authorize(
        receipt, protocol, g0_return, control, immutable, item,
        protocol_verifier=lambda _: {
            "candidate_sha256": item["candidate_sha256"],
            "protocol_content_sha256": item["protocol_content_sha256"],
        },
        return_verifier=lambda *_: ({"comparison_sha256": "5" * 64}, "4" * 64),
    )


def root_pass(root: Path, item: dict) -> dict:
    return {"status": "PASS", "candidate_sha256": item["candidate_sha256"], "immutable": True}


def environment_pass(root: Path, item: dict, install_wheel: bool = True) -> dict:
    return {"status": "PASS", "candidate_sha256": item["candidate_sha256"], "installed": install_wheel}


def authorize(tmp_path: Path):
    immutable, protocol, control, item, receipt, g0_return = fixture(tmp_path)
    immutable_before = {
        path.relative_to(immutable).as_posix(): sha256_file(path)
        for path in immutable.rglob("*") if path.is_file()
    }
    commit_fixture_authorization(receipt, protocol, g0_return, control, immutable, item)
    immutable_after = {
        path.relative_to(immutable).as_posix(): sha256_file(path)
        for path in immutable.rglob("*") if path.is_file()
    }
    assert immutable_after == immutable_before
    return immutable, protocol, control, item, receipt


def test_valid_production_lifecycle_reaches_runner_exactly_once(tmp_path: Path) -> None:
    immutable, _, control, item, _ = authorize(tmp_path)
    authorization = load_authorization(control, item, immutable)
    calls = []

    def runner():
        calls.append("RUN")
        return 0, "RUNNER_STUB_EXECUTED_ONCE"

    terminal = execute_once(
        item, authorization, control, runner, immutable,
        root_verifier=root_pass, environment_verifier=environment_pass,
    )
    assert calls == ["RUN"]
    assert terminal["status"] == "PASSED"
    assert verify_control_root(control, item, "TERMINAL", immutable)["status"] == "PASS"
    assert not list(immutable.rglob("AUTHORIZATION.json"))


def test_setup_failure_does_not_reserve_attempt_or_run(tmp_path: Path) -> None:
    immutable, _, control, item, _ = authorize(tmp_path)
    authorization = load_authorization(control, item, immutable)
    calls = []

    def bad_environment(*args, **kwargs):
        raise RuntimeError("setup failed")

    with pytest.raises(RuntimeError, match="setup failed"):
        execute_once(
            item, authorization, control, lambda: calls.append("RUN"), immutable,
            root_verifier=root_pass, environment_verifier=bad_environment,
        )
    namespace = candidate_control_root(control, item, immutable)
    assert not (namespace / STATE_NAME).exists()
    assert calls == []


def test_wrong_candidate_receipt_fails_before_control_commit(tmp_path: Path) -> None:
    immutable, protocol, control, item, receipt, g0_return = fixture(tmp_path)
    payload = json.loads(receipt.read_text())
    payload["candidate_sha256"] = "0" * 64
    receipt.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="identity, decision, or scope"):
        commit_fixture_authorization(receipt, protocol, g0_return, control, immutable, item)
    assert not control.exists()


@pytest.mark.parametrize("mutation", [
    "extra", "missing", "receipt-replay", "wrong-candidate", "stale-authorization",
    "control-symlink",
])
def test_control_plane_mutations_fail_closed(tmp_path: Path, mutation: str) -> None:
    immutable, _, control, item, receipt = authorize(tmp_path)
    namespace = candidate_control_root(control, item, immutable)
    if mutation == "extra":
        (namespace / "EXTRA.txt").write_text("unlisted\n")
    elif mutation == "missing":
        (namespace / AUTHORIZATION_NAME).unlink()
    elif mutation == "receipt-replay":
        with pytest.raises(RuntimeError, match="already exists"):
            commit_fixture_authorization(receipt, tmp_path / "protocol.zip", tmp_path / "complete-g0-return.zip", control, immutable, item)
        return
    elif mutation == "wrong-candidate":
        authorization = json.loads((namespace / AUTHORIZATION_NAME).read_text())
        authorization["candidate_sha256"] = "0" * 64
        authorization["authorization_sha256"] = sha256_payload({
            key: value for key, value in authorization.items() if key != "authorization_sha256"
        })
        (namespace / AUTHORIZATION_NAME).write_text(json.dumps(authorization) + "\n")
    elif mutation == "stale-authorization":
        authorization = json.loads((namespace / AUTHORIZATION_NAME).read_text())
        authorization["receipt_id"] = "stale-receipt-id"
        authorization["authorization_sha256"] = sha256_payload({
            key: value for key, value in authorization.items() if key != "authorization_sha256"
        })
        (namespace / AUTHORIZATION_NAME).write_text(json.dumps(authorization) + "\n")
    elif mutation == "control-symlink":
        original = namespace / RECEIPT_NAME
        copy_path = tmp_path / "receipt-copy.json"
        copy_path.write_bytes(original.read_bytes())
        original.unlink()
        original.symlink_to(copy_path)
    with pytest.raises(RuntimeError):
        verify_control_root(control, item, "AUTHORIZED", immutable)


def test_concurrent_or_repeated_launch_cannot_reserve_twice(tmp_path: Path) -> None:
    immutable, _, control, item, _ = authorize(tmp_path)
    authorization = load_authorization(control, item, immutable)
    execute_once(
        item, authorization, control, lambda: (0, "first"), immutable,
        root_verifier=root_pass, environment_verifier=environment_pass,
    )
    with pytest.raises(RuntimeError):
        execute_once(
            item, authorization, control, lambda: (0, "second"), immutable,
            root_verifier=root_pass, environment_verifier=environment_pass,
        )


def test_execution_contract_mismatch_fails_before_reservation(tmp_path: Path) -> None:
    immutable, _, control, item, _ = authorize(tmp_path)
    authorization = load_authorization(control, item, immutable)
    (immutable / item["authorization_contract"]["runner"]["path"]).write_text(
        "mutated runner\n", encoding="utf-8"
    )
    with pytest.raises(RuntimeError, match="runner contract identity"):
        execute_once(
            item, authorization, control, lambda: (0, "must not run"), immutable,
            root_verifier=root_pass, environment_verifier=environment_pass,
        )
    namespace = candidate_control_root(control, item, immutable)
    assert not (namespace / STATE_NAME).exists()


def test_control_root_ancestor_symlink_fails_closed(tmp_path: Path) -> None:
    immutable, protocol, _, item, receipt, g0_return = fixture(tmp_path)
    real = tmp_path / "real-control"
    real.mkdir()
    linked = tmp_path / "linked-control"
    linked.symlink_to(real, target_is_directory=True)
    with pytest.raises(RuntimeError, match="symlinked"):
        commit_fixture_authorization(receipt, protocol, g0_return, linked, immutable, item)


def test_invalid_terminal_artifact_manifest_fails_closed(tmp_path: Path) -> None:
    immutable, _, control, item, _ = authorize(tmp_path)
    authorization = load_authorization(control, item, immutable)
    terminal = execute_once(
        item, authorization, control, lambda: (0, "valid"), immutable,
        root_verifier=root_pass, environment_verifier=environment_pass,
    )
    namespace = candidate_control_root(control, item, immutable)
    manifest = namespace / terminal["artifact_path"] / "ARTIFACT_MANIFEST.json"
    payload = json.loads(manifest.read_text())
    payload["transcript_sha256"] = "0" * 64
    payload["manifest_sha256"] = sha256_payload({
        key: value for key, value in payload.items() if key != "manifest_sha256"
    })
    manifest.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="artifact manifest"):
        verify_control_root(control, item, "TERMINAL", immutable)


def test_runner_failure_terminalizes_once_and_does_not_retry(tmp_path: Path) -> None:
    immutable, _, control, item, _ = authorize(tmp_path)
    authorization = load_authorization(control, item, immutable)
    calls = []

    def failed_runner():
        calls.append("RUN")
        return 7, "declared runner failure"

    with pytest.raises(RuntimeError, match="exit status 7"):
        execute_once(
            item, authorization, control, failed_runner, immutable,
            root_verifier=root_pass, environment_verifier=environment_pass,
        )
    assert calls == ["RUN"]
    assert verify_control_root(control, item, "TERMINAL", immutable)["status"] == "PASS"
    namespace = candidate_control_root(control, item, immutable)
    state = json.loads((namespace / STATE_NAME).read_text())
    assert state["status"] == "FAILED"


def test_two_concurrent_launches_execute_runner_once(tmp_path: Path) -> None:
    immutable, _, control, item, _ = authorize(tmp_path)
    authorization = load_authorization(control, item, immutable)
    runner_calls = []
    outcomes = []
    barrier = threading.Barrier(2)

    def launch() -> None:
        barrier.wait()
        try:
            execute_once(
                item, authorization, control,
                lambda: (runner_calls.append("RUN") or 0, "concurrent"),
                immutable, root_verifier=root_pass,
                environment_verifier=environment_pass,
            )
            outcomes.append("PASS")
        except RuntimeError:
            outcomes.append("REJECTED")

    threads = [threading.Thread(target=launch) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(outcomes) == ["PASS", "REJECTED"]
    assert runner_calls == ["RUN"]


def test_scientific_artifacts_are_closed_in_terminal_manifest(tmp_path: Path) -> None:
    immutable, _, control, item, _ = authorize(tmp_path)
    authorization = load_authorization(control, item, immutable)
    scientific = tmp_path / "scientific-output"
    scientific.mkdir()
    (scientific / "decision.json").write_text('{"status":"PASS"}\n', encoding="utf-8")
    nested = scientific / "tables"
    nested.mkdir()
    (nested / "curve.csv").write_text("time,value\n0,1\n", encoding="utf-8")

    terminal = execute_once(
        item, authorization, control,
        lambda: (0, "scientific runner passed", scientific), immutable,
        root_verifier=root_pass, environment_verifier=environment_pass,
    )
    namespace = candidate_control_root(control, item, immutable)
    artifact = namespace / terminal["artifact_path"]
    manifest = json.loads((artifact / "ARTIFACT_MANIFEST.json").read_text())
    assert set(manifest["scientific_files"]) == {"decision.json", "tables/curve.csv"}
    assert (artifact / "scientific/decision.json").is_file()
    assert verify_control_root(control, item, "TERMINAL", immutable)["status"] == "PASS"
