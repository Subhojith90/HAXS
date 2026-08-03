from __future__ import annotations

import copy
import json
import stat
import sys
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from build_stage5c2gR32A1_candidate import (
    RETIRED_EXECUTABLES,
    ROOT_CONTRACTS,
    closure_paths,
    runtime_paths,
)
from stage5c2gR32A1_authorization import (
    BLOCKED_SCOPES,
    RECEIPT_KEYS,
    load_and_validate_receipt,
    validate_receipt_payload,
)
from verify_stage5c2gR32A1_fresh_unzip import (
    PREFIX,
    validate_archive_entries,
    validate_strict_root,
)

SHA = "a" * 64


def candidate() -> dict:
    contracts = {
        name: {"path": f"fixture/{name}", "sha256": SHA}
        for name in [
            "receipt_template",
            "finalizer",
            "launcher",
            "runner",
            "g1_config",
            "g1_plan",
            "unit_registry",
            "test_ledger",
            "root_manifest",
        ]
    }
    return {
        "schema_version": "haxs.stage5c2gR32A1.candidate.v1",
        "candidate_sha256": SHA,
        "runtime_tree_sha256": SHA,
        "wheel": {"path": "fixture.whl", "sha256": SHA},
        "environment": {"path": "environment.json", "sha256": SHA},
        "authorization_contract": contracts,
    }


def valid_receipt() -> dict:
    return {
        "schema_version": "haxs.stage5c2gR32A1.authorization.v1",
        "receipt_id": str(uuid.uuid4()),
        "decision": "ACCEPT_AND_AUTHORIZE_G1_ONLY",
        "candidate_sha256": SHA,
        "protocol_archive_sha256": SHA,
        "runtime_tree_sha256": SHA,
        "wheel_sha256": SHA,
        "environment_sha256": SHA,
        "g1_config_sha256": SHA,
        "g1_plan_sha256": SHA,
        "unit_registry_sha256": SHA,
        "runner_sha256": SHA,
        "test_ledger_sha256": SHA,
        "two_host_g0_sha256": SHA,
        "authorized_scope": "G1_ONLY",
        "blocked_scopes": list(BLOCKED_SCOPES),
        "issued_at_utc": datetime.now(timezone.utc).isoformat(),
        "issuer": {"name": "Supervisor Fixture", "role": "SUPERVISOR"},
    }


def test_exact_key_valid_current_stage_receipt_is_accepted() -> None:
    receipt = valid_receipt()
    assert set(receipt) == RECEIPT_KEYS
    assert validate_receipt_payload(receipt, candidate(), SHA, SHA) == receipt


MUTATIONS = [
    ("schema_version", "haxs.stage5c2gR32.authorization.v1"),
    ("decision", "REJECT"),
    ("candidate_sha256", "b" * 64),
    ("protocol_archive_sha256", "b" * 64),
    ("runtime_tree_sha256", "b" * 64),
    ("wheel_sha256", "b" * 64),
    ("environment_sha256", "b" * 64),
    ("g1_config_sha256", "b" * 64),
    ("g1_plan_sha256", "b" * 64),
    ("unit_registry_sha256", "b" * 64),
    ("runner_sha256", "b" * 64),
    ("test_ledger_sha256", "b" * 64),
    ("two_host_g0_sha256", "b" * 64),
    ("authorized_scope", "G1_G2"),
    ("blocked_scopes", BLOCKED_SCOPES[:-1]),
    ("receipt_id", "not-a-uuid"),
    ("issued_at_utc", "2026-07-30T12:00:00"),
    ("issuer", {"name": "", "role": "SUPERVISOR"}),
    ("issuer", {"name": "Supervisor Fixture", "role": "STUDENT"}),
]


@pytest.mark.parametrize(("field", "value"), MUTATIONS)
def test_each_invalid_receipt_fixture_fails_closed(field: str, value: object) -> None:
    receipt = valid_receipt()
    receipt[field] = value
    with pytest.raises(RuntimeError):
        validate_receipt_payload(receipt, candidate(), SHA, SHA)


def test_missing_and_additional_receipt_keys_fail_closed() -> None:
    missing = valid_receipt()
    missing.pop("runner_sha256")
    extra = valid_receipt()
    extra["comment"] = "not part of the frozen schema"
    with pytest.raises(RuntimeError, match="missing or additional"):
        validate_receipt_payload(missing, candidate(), SHA, SHA)
    with pytest.raises(RuntimeError, match="missing or additional"):
        validate_receipt_payload(extra, candidate(), SHA, SHA)


def test_receipt_replay_against_another_candidate_fails_closed() -> None:
    other = copy.deepcopy(candidate())
    other["candidate_sha256"] = "c" * 64
    with pytest.raises(RuntimeError, match="candidate_sha256"):
        validate_receipt_payload(valid_receipt(), other, SHA, SHA)


def test_malformed_duplicate_and_symlink_receipts_fail_closed(
    tmp_path: Path,
) -> None:
    malformed = tmp_path / "malformed.json"
    malformed.write_text("{", encoding="utf-8")
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text(
        '{"schema_version":"x","schema_version":"y"}', encoding="utf-8"
    )
    symlink = tmp_path / "receipt-link.json"
    symlink.symlink_to(malformed)
    for path in [malformed, duplicate, symlink]:
        with pytest.raises(RuntimeError):
            load_and_validate_receipt(path, candidate(), SHA, SHA)


def test_runtime_root_contracts_and_custody_are_self_contained() -> None:
    runtime = {path.relative_to(ROOT).as_posix() for path in runtime_paths()}
    assert set(ROOT_CONTRACTS).issubset(runtime)
    assert RETIRED_EXECUTABLES.isdisjoint(runtime)
    closure = closure_paths()
    assert len(closure) == 7
    assert all(path.is_file() and not path.is_symlink() for path in closure)


def _archive(path: Path, entries: list[tuple[str, int]]) -> None:
    with zipfile.ZipFile(path, "w") as handle:
        for name, mode in entries:
            info = zipfile.ZipInfo(name)
            info.external_attr = mode << 16
            handle.writestr(info, b"x")


@pytest.mark.parametrize(
    "entries",
    [
        [(f"{PREFIX}/../escape.py", stat.S_IFREG | 0o644)],
        [(f"{PREFIX}/hook.py", stat.S_IFLNK | 0o777)],
        [(f"{PREFIX}/__pycache__/hook.pyc", stat.S_IFREG | 0o644)],
        [("outside/hook.py", stat.S_IFREG | 0o644)],
        [
            (f"{PREFIX}/duplicate.py", stat.S_IFREG | 0o644),
            (f"{PREFIX}/duplicate.py", stat.S_IFREG | 0o644),
        ],
    ],
)
def test_unsafe_archive_entries_fail_closed(
    tmp_path: Path, entries: list[tuple[str, int]]
) -> None:
    archive = tmp_path / "fixture.zip"
    _archive(archive, entries)
    with zipfile.ZipFile(archive) as handle:
        with pytest.raises(RuntimeError):
            validate_archive_entries(handle)


def test_predecessor_finalizer_and_launcher_are_not_current_stage_routes() -> None:
    finalizer = (
        ROOT / "scripts/finalize_stage5c2gR32A1_authorization.py"
    ).read_text(encoding="utf-8")
    launcher = (
        ROOT / "scripts/launch_stage5c2gR32A1_G1_isolated.py"
    ).read_text(encoding="utf-8")
    assert "stage5c2gR32A1_authorization" in finalizer
    assert "run_stage5c2gR32A1_G1.py" in launcher
    assert "run_stage5c2gR32_phase_quadrature.py" not in launcher


def _strict_root_fixture(tmp_path: Path) -> tuple[dict, dict]:
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts/runner.py").write_text("pass\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("fixture\n", encoding="utf-8")
    candidate_record = {
        "runtime_files": {
            "scripts/runner.py": "fixture",
            "README.md": "fixture",
        }
    }
    manifest = {
        "allowed_top_level_entries": ["README.md", "scripts"],
        "forbidden_root_hooks": [
            "conftest.py",
            "sitecustomize.py",
            "usercustomize.py",
        ],
    }
    return candidate_record, manifest


def test_strict_root_valid_fixture_is_accepted(tmp_path: Path) -> None:
    candidate_record, manifest = _strict_root_fixture(tmp_path)
    validate_strict_root(tmp_path, candidate_record, manifest)


def test_strict_root_extra_hook_fails_closed(tmp_path: Path) -> None:
    candidate_record, manifest = _strict_root_fixture(tmp_path)
    (tmp_path / "sitecustomize.py").write_text("raise SystemExit\n", encoding="utf-8")
    with pytest.raises(RuntimeError):
        validate_strict_root(tmp_path, candidate_record, manifest)


def test_strict_root_missing_required_entry_fails_closed(tmp_path: Path) -> None:
    candidate_record, manifest = _strict_root_fixture(tmp_path)
    (tmp_path / "README.md").unlink()
    with pytest.raises(RuntimeError, match="top-level mismatch"):
        validate_strict_root(tmp_path, candidate_record, manifest)


def test_strict_root_unlisted_nested_executable_fails_closed(tmp_path: Path) -> None:
    candidate_record, manifest = _strict_root_fixture(tmp_path)
    (tmp_path / "scripts/injected.py").write_text("pass\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="unlisted or missing"):
        validate_strict_root(tmp_path, candidate_record, manifest)


def test_strict_root_symlink_fails_closed(tmp_path: Path) -> None:
    candidate_record, manifest = _strict_root_fixture(tmp_path)
    (tmp_path / "scripts/link.py").symlink_to(tmp_path / "scripts/runner.py")
    with pytest.raises(RuntimeError, match="symlink"):
        validate_strict_root(tmp_path, candidate_record, manifest)
