from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import finalize_stage5c2gR32A4_authorization as finalizer
import package_stage5c2gR32A4_supervisor_return as packager
import stage5c2gR32A4_g0 as g0_semantics
from stage5c2gR32A4_common import sha256_file, sha256_payload
from stage5c2gR32A4_g0 import verify_host_record


def test_official_finalizer_accepts_zip_objects_only() -> None:
    source = inspect.getsource(finalizer.authorize)
    assert "g0_return.is_dir()" not in source
    assert "zipfile.ZipFile(g0_return)" in source


def test_complete_return_packager_binds_raw_primary_evidence() -> None:
    source = inspect.getsource(packager) + inspect.getsource(g0_semantics.verify_host_record)
    for required in [
        "full_junit", "targeted_junit", "named_test_ledger", "command_records",
        "protocol_content_sha256", "transport_container_sha256",
    ]:
        assert required in source


def test_local_two_host_dry_run_executes_from_fresh_protocol_root() -> None:
    source = (ROOT / "scripts/dry_run_stage5c2gR32A4_complete_return.py").read_text(
        encoding="utf-8"
    )
    assert "execution_root / \"scripts/run_stage5c2gR32A4_g0.py\"" in source
    assert "cwd=execution_root" in source
    assert "_safe_extract(handle, Path(directory))" in source
    assert 'str(ROOT / "scripts/run_stage5c2gR32A4_g0.py")' not in source
    assert "packaging_root / \"scripts/package_stage5c2gR32A4_supervisor_return.py\"" in source
    assert "cwd=packaging_root" in source


def test_current_stage_release_and_return_entrypoints_exist() -> None:
    for relative in [
        "scripts/package_stage5c2gR32A4_host_b_release.py",
        "scripts/package_stage5c2gR32A4_supervisor_return.py",
        "scripts/dry_run_stage5c2gR32A4_complete_return.py",
        "ci/run_stage5c2gR32A4_github_host_b_g0.sh",
        ".github/workflows/stage5c2gR32A4-host-b-g0.yml",
    ]:
        assert (ROOT / relative).is_file()


def test_complete_return_tampering_fails_before_comparison(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "return"
    root.mkdir()
    payload = root / "payload.txt"
    payload.write_text("primary evidence\n", encoding="utf-8")
    comparison = {"status": "PASS", "comparison_sha256": "c" * 64}
    (root / "TWO_HOST_G0.json").write_text(json.dumps(comparison) + "\n")
    protocol = root / "protocol.zip"
    protocol.write_bytes(b"synthetic protocol fixture")
    protocol_sha = sha256_file(protocol)
    files = {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in sorted(root.rglob("*")) if path.is_file()
    }
    candidate = {"candidate_sha256": "a" * 64, "protocol_content_sha256": "b" * 64}
    record = {
        "schema_version": "haxs.stage5c2gR32A4.complete-g0-return.v1",
        "candidate_sha256": candidate["candidate_sha256"],
        "protocol_archive_sha256": protocol_sha,
        "protocol_content_sha256": candidate["protocol_content_sha256"],
        "transport_container_sha256": sha256_payload(files),
        "protocol_path": "protocol.zip",
        "host_a_path": "HOST_A.json", "host_b_path": "HOST_B.json",
        "comparison_path": "TWO_HOST_G0.json", "files": files,
        "scientific_execution_performed": False, "G1_authorized": False,
        "synthetic_dry_run": True, "return_sha256": "",
    }
    record["return_sha256"] = sha256_payload(
        {key: value for key, value in record.items() if key != "return_sha256"}
    )
    (root / "G0_RETURN.json").write_text(json.dumps(record) + "\n")
    monkeypatch.setattr(finalizer, "recompute_two_host_g0", lambda *args: comparison)
    monkeypatch.setattr(finalizer, "finalize_comparison", lambda value: value)
    verified, _ = finalizer.verify_complete_g0_return(
        root, candidate, protocol_sha, allow_synthetic=True,
    )
    assert verified == comparison
    payload.write_text("tampered\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="file manifest"):
        finalizer.verify_complete_g0_return(
            root, candidate, protocol_sha, allow_synthetic=True,
        )


def test_stale_predecessor_host_package_is_rejected(tmp_path: Path) -> None:
    host = tmp_path / "HOST_B.json"
    host.write_text(json.dumps({
        "schema_version": "haxs.stage5c2gR32A3.physical-host-g0.v1",
        "status": "PASS", "host_label": "HOST_B",
    }) + "\n")
    with pytest.raises(RuntimeError, match="R3.2A.4 schema"):
        verify_host_record(
            host, tmp_path, {"candidate_sha256": "a" * 64},
            "HOST_B", "b" * 64,
        )
