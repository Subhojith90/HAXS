from __future__ import annotations

import ast
import json
import multiprocessing
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2gR3_common import assert_execution_root_closed, assert_runtime_tree_matches, environment_spec, load_yaml, plan_g1, scan_runtime_tree, sha256_file, sha256_payload, verify_environment
from stage5c2gR3_semantics import derive_g1_decision
from stage5c2gR3_semantics_reference import assert_semantic_agreement, derive_g1_decision_reference
from stage5c2gR3_state import _safe_relative, assert_canonical_artifact_root, atomic_write_json, begin_attempt, build_raw_manifest, canonical_artifact_root, fail_attempt, recompute_g1_semantics, verify_raw_manifest
from stage5c2gR3_receipt import load_and_validate_receipt
from verify_stage5c2gR3_1_two_physical_hosts import verify_two_hosts


def concurrent_begin_worker(root: str, attempt_id: str, start, queue) -> None:
    start.wait()
    try:
        state = begin_attempt("G1", {"candidate_sha256": "a" * 64}, "c", "p", attempt_id, Path(root)); queue.put(("success", state["attempt_id"]))
    except Exception as error:
        queue.put(("rejected", str(error)))


def canonical_g1() -> dict:
    return load_yaml("configs/stage5c2gR3/g1.yaml", ROOT)


def fake_lock(tmp_path: Path) -> tuple[dict, str, str]:
    config = canonical_g1(); relative = "configs/stage5c2gR3/g1.yaml"; target = tmp_path / relative; target.parent.mkdir(parents=True); target.write_text((ROOT / relative).read_text(), encoding="utf-8")
    config_sha = sha256_file(target); plan_sha = sha256_payload(plan_g1(config))
    lock = {"candidate_sha256": "a" * 64, "candidate_payload": {"canonical_configs": {"G1": {"path": relative, "sha256": config_sha}}, "expected_plans": {"G1": {"sha256": plan_sha, "rows": len(plan_g1(config))}}}}
    return lock, config_sha, plan_sha


def write_semantic_fixture(tmp_path: Path, corrupt: bool = False, common_curve: str = "physical") -> tuple[dict, Path, str, str]:
    lock, config_sha, plan_sha = fake_lock(tmp_path); config = canonical_g1(); stage = config["stage5c2gR3_G1"]; plan = plan_g1(config); attempt_id = "b" * 32
    root = canonical_artifact_root("G1", lock, config_sha, attempt_id, tmp_path); root.mkdir(parents=True)
    times = np.linspace(stage["times"]["start"], stage["times"]["stop"], stage["times"]["points"]); curve_rows = []
    for planned in plan:
        columns = stage["method_value_columns"][planned["method"]]
        case = next(value for value in stage["cases"] if value["id"] == planned["case_id"])
        particles = float(np.prod(case["shape"]) - len(case["holes"]))
        for label in [planned["static_label"], planned["comparison_label"]]:
            for time in times:
                row = {"schema_version": stage["schema_version"], "comparison_id": planned["comparison_id"], "label": label, "method": planned["method"], "time": time}
                if common_curve == "physical":
                    sx = particles / 2.0 * (1.0 - 0.05 * float(time))
                    xi2 = 1.0 - 0.10 * float(time)
                    min_var = xi2 * sx * sx / particles
                    row.update({"Sx": sx, "Sy": 0.0, "Sz": 0.0, "xi2": xi2, "xi2_db": 10.0 * np.log10(xi2), "min_var": min_var, "spin_length": 2.0 * sx / particles})
                    if planned["method"] == "exact": row.update({"particle_number": particles, "norm_error": 0.0, "hole_number_expectation": float(len(case["holes"]))})
                    else: row.update({"N_eff": particles, "active_bonds": 2.0, "hole_spin_covariance": 0.0})
                else:
                    value = 0.0 if common_curve == "zeros" else 999.0
                    row.update({column: value for column in columns})
                if corrupt and label == planned["comparison_label"]: row[columns[0]] = 999.0
                curve_rows.append(row)
    files = {"curves": root / "curves.csv", "comparisons": root / "comparisons.csv", "registry": root / "registry.csv", "attempts": root / "attempts.csv", "semantic_decision": root / "decision.json", "runtime_attestation": root / "runtime_attestation.json"}
    pd.DataFrame(curve_rows).to_csv(files["curves"], index=False)
    pd.DataFrame({"comparison_id": [row["comparison_id"] for row in plan], "stored_pass": True}).to_csv(files["comparisons"], index=False)
    pd.DataFrame(plan).to_csv(files["registry"], index=False)
    pd.DataFrame({"comparison_id": [row["comparison_id"] for row in plan], "status": "completed"}).to_csv(files["attempts"], index=False)
    decision = derive_g1_decision(files["curves"], files["registry"], config); atomic_write_json(files["semantic_decision"], decision)
    atomic_write_json(files["runtime_attestation"], {"schema_version": "test", "rows": []})
    ids = [row["comparison_id"] for row in plan]; manifest = build_raw_manifest("G1", root, files, ids, ids, lock, config_sha, plan_sha, attempt_id, tmp_path); atomic_write_json(root / "MANIFEST.json", manifest)
    return lock, root, attempt_id, (root / "MANIFEST.json").relative_to(tmp_path).as_posix()


def test_primary_and_reference_semantics_agree_on_canonical_physical_curves(tmp_path: Path) -> None:
    lock, root, _, _ = write_semantic_fixture(tmp_path); config = canonical_g1()
    primary = derive_g1_decision(root / "curves.csv", root / "registry.csv", config); reference = derive_g1_decision_reference(root / "curves.csv", root / "registry.csv", config)
    assert_semantic_agreement(primary, reference); assert primary["passed"] and primary["maximum_difference"] == 0.0


@pytest.mark.parametrize("common_curve", ["zeros", "constant999"])
def test_paired_arbitrary_common_curves_fail_absolute_sanity(tmp_path: Path, common_curve: str) -> None:
    _, root, _, _ = write_semantic_fixture(tmp_path, common_curve=common_curve)
    primary = derive_g1_decision(root / "curves.csv", root / "registry.csv", canonical_g1())
    reference = derive_g1_decision_reference(root / "curves.csv", root / "registry.csv", canonical_g1())
    assert_semantic_agreement(primary, reference)
    assert primary["equality_passed"] is True
    assert primary["absolute_sanity_passed"] is False
    assert primary["passed"] is False


def test_self_consistent_999_curves_fail_semantic_authorization(tmp_path: Path) -> None:
    lock, root, _, manifest_relative = write_semantic_fixture(tmp_path, corrupt=True)
    manifest = json.loads((tmp_path / manifest_relative).read_text())
    with pytest.raises(RuntimeError, match="scientific authorization predicate failed"): recompute_g1_semantics(manifest, root, canonical_g1())


def test_single_writer_and_cas_reject_concurrent_and_stale_completion(tmp_path: Path) -> None:
    lock = {"candidate_sha256": "a" * 64}; first = begin_attempt("G1", lock, "c", "p", "1" * 32, tmp_path)
    with pytest.raises(RuntimeError, match="single-writer"): begin_attempt("G1", lock, "c", "p", "2" * 32, tmp_path)
    fail_attempt("G1", lock, "1" * 32, first["sequence"], "first failed", tmp_path)
    second = begin_attempt("G1", lock, "c", "p", "2" * 32, tmp_path); fail_attempt("G1", lock, "2" * 32, second["sequence"], "newer failed", tmp_path)
    with pytest.raises(RuntimeError, match="compare-and-swap"): fail_attempt("G1", lock, "1" * 32, first["sequence"], "stale overwrite", tmp_path)


def test_two_processes_cannot_both_begin_the_same_gate(tmp_path: Path) -> None:
    context = multiprocessing.get_context("fork"); start = context.Event(); queue = context.Queue()
    processes = [context.Process(target=concurrent_begin_worker, args=(str(tmp_path), value * 32, start, queue)) for value in ["1", "2"]]
    for process in processes: process.start()
    start.set()
    results = [queue.get(timeout=10) for _ in processes]
    for process in processes: process.join(timeout=10)
    assert sorted(result[0] for result in results) == ["rejected", "success"]


@pytest.mark.parametrize("value", ["/tmp/external/MANIFEST.json", "../MANIFEST.json", "results/../MANIFEST.json"])
def test_absolute_and_parent_traversal_manifest_paths_are_rejected(value: str) -> None:
    with pytest.raises(RuntimeError, match="unsafe|absolute"): _safe_relative(value)


def test_recursive_manifest_rejects_nested_unlisted_file(tmp_path: Path) -> None:
    lock, root, attempt_id, manifest_relative = write_semantic_fixture(tmp_path); nested = root / "nested"; nested.mkdir(); (nested / "extra.py").write_text("x=1\n")
    with pytest.raises(RuntimeError, match="recursive evidence tree"): verify_raw_manifest(manifest_relative, lock, "G1", attempt_id, tmp_path)


def test_manifest_rejects_missing_file_and_symlink_record(tmp_path: Path) -> None:
    lock, root, attempt_id, manifest_relative = write_semantic_fixture(tmp_path); curves = root / "curves.csv"; backup = tmp_path / "external_curves.csv"; curves.replace(backup)
    with pytest.raises(RuntimeError, match="changed or missing"): verify_raw_manifest(manifest_relative, lock, "G1", attempt_id, tmp_path)
    os.symlink(backup, curves)
    with pytest.raises(RuntimeError, match="symlink"): verify_raw_manifest(manifest_relative, lock, "G1", attempt_id, tmp_path)


def test_canonical_attempt_root_symlink_is_rejected(tmp_path: Path) -> None:
    lock, config_sha, _ = fake_lock(tmp_path); attempt_id = "b" * 32
    canonical = canonical_artifact_root("G1", lock, config_sha, attempt_id, tmp_path)
    external = tmp_path / "external_attempt"; external.mkdir()
    canonical.parent.mkdir(parents=True); os.symlink(external, canonical)
    with pytest.raises(RuntimeError, match="symlink"):
        assert_canonical_artifact_root(canonical, tmp_path)


def test_duplicate_registry_id_fails_even_with_complete_rows_and_hashes(tmp_path: Path) -> None:
    _, root, _, _ = write_semantic_fixture(tmp_path); registry = pd.read_csv(root / "registry.csv"); registry.loc[1, "comparison_id"] = registry.loc[0, "comparison_id"]; registry.to_csv(root / "registry.csv", index=False)
    with pytest.raises(RuntimeError, match="unique canonical comparison plan"): derive_g1_decision(root / "curves.csv", root / "registry.csv", canonical_g1())


def minimal_runtime_root(tmp_path: Path) -> Path:
    (tmp_path / "configs/stage5c2gR3").mkdir(parents=True); (tmp_path / "src/pkg").mkdir(parents=True); (tmp_path / "scripts").mkdir(); (tmp_path / "tests").mkdir(); (tmp_path / "docs/stage5c2gR3").mkdir(parents=True)
    protocol = {"stage5c2gR3_protocol": {"runtime_roots": ["src", "scripts", "tests", "configs", "docs/stage5c2gR3"], "runtime_root_files": []}}
    (tmp_path / "configs/stage5c2gR3/protocol.yaml").write_text(yaml.safe_dump(protocol)); (tmp_path / "src/pkg/model.py").write_text("x=1\n")
    return tmp_path


@pytest.mark.parametrize("relative", ["src/pkg/shadow.so", "src/hook.pth", "src/pkg/loader.loader", "src/pkg/native.dylib"])
def test_native_and_loader_artifacts_are_denied(tmp_path: Path, relative: str) -> None:
    root = minimal_runtime_root(tmp_path); path = root / relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(b"unsafe")
    with pytest.raises(RuntimeError, match="native/loader"): scan_runtime_tree(root)


def test_hidden_package_extensionless_executable_and_symlink_are_denied(tmp_path: Path) -> None:
    root = minimal_runtime_root(tmp_path); hidden = root / "src/.shadow/__init__.py"; hidden.parent.mkdir(); hidden.write_text("")
    with pytest.raises(RuntimeError, match="hidden"): scan_runtime_tree(root)
    hidden.unlink(); hidden.parent.rmdir(); executable = root / "scripts/runner"; executable.write_text("x"); executable.chmod(0o755)
    with pytest.raises(RuntimeError, match="extensionless"): scan_runtime_tree(root)
    executable.unlink(); os.symlink(root / "src/pkg/model.py", root / "src/pkg/link.py")
    with pytest.raises(RuntimeError, match="symlink"): scan_runtime_tree(root)


def test_generated_install_metadata_is_denied_and_tree_identity_is_exact(tmp_path: Path) -> None:
    root = minimal_runtime_root(tmp_path); baseline = scan_runtime_tree(root); egg = root / "src/haxs.egg-info"; egg.mkdir(); (egg / "SOURCES.txt").write_text("mutated")
    with pytest.raises(RuntimeError, match="generated package metadata"): scan_runtime_tree(root)
    egg.joinpath("SOURCES.txt").unlink(); egg.rmdir(); (root / "src/pkg/new.py").write_text("x=2\n")
    with pytest.raises(RuntimeError, match="exact runtime tree"): assert_runtime_tree_matches(baseline, root)


def test_unknown_runtime_suffix_is_denied(tmp_path: Path) -> None:
    root = minimal_runtime_root(tmp_path); (root / "src/pkg/unknown.bin").write_bytes(b"unknown")
    with pytest.raises(RuntimeError, match="unknown runtime artifact"): scan_runtime_tree(root)


def test_unlisted_repository_root_hook_is_rejected(tmp_path: Path) -> None:
    root = minimal_runtime_root(tmp_path); (root / "conftest.py").write_text("raise RuntimeError('external hook executed')\n")
    with pytest.raises(RuntimeError, match="execution root closure"):
        assert_execution_root_closed(root)


def test_external_pythonpath_shim_cannot_pass_static_gate(tmp_path: Path) -> None:
    shim = tmp_path / "yaml.py"; marker = tmp_path / "external_marker.txt"
    shim.write_text(f"from pathlib import Path\nPath({str(marker)!r}).write_text('executed')\n")
    environment = os.environ.copy(); environment["PYTHONPATH"] = str(tmp_path)
    result = subprocess.run([sys.executable, "-I", "scripts/check_stage5c2gR3_static_gate.py"], cwd=ROOT, env=environment, capture_output=True, text=True)
    assert result.returncode != 0
    assert "not scrubbed" in result.stdout + result.stderr
    assert not marker.exists()


def test_every_python_file_must_parse() -> None:
    for relative in scan_runtime_tree(ROOT)["files"]:
        if relative.endswith(".py"): ast.parse((ROOT / relative).read_text(encoding="utf-8"), filename=relative)


def test_packaged_full_suite_dependencies_are_runtime_bound() -> None:
    tree = scan_runtime_tree(ROOT)["files"]
    required = {
        "STAGE3_COMMANDS.sh",
        "STAGE3A_COMMANDS.sh",
        "requirements-stage5c2gR2.lock",
        "scripts_patch/stage5c2eR_patch.py",
        "docs/stage5aR/STAGE5AR_RUNBOOK.md",
    }
    assert required <= set(tree)


def test_wrong_platform_and_thread_identity_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = json.loads(json.dumps(environment_spec(ROOT))); spec["platform_machine"] = "wrong-machine"
    with pytest.raises(RuntimeError, match="environment identity mismatch"): verify_environment(spec)
    spec = environment_spec(ROOT); monkeypatch.setenv("OMP_NUM_THREADS", "999")
    with pytest.raises(RuntimeError, match="OMP_NUM_THREADS"): verify_environment(spec)


def test_modified_candidate_metadata_changes_external_identity() -> None:
    payload = {"candidate": "original", "semantic_analyzer_sha256": "a" * 64}; original = sha256_payload(payload); payload["semantic_analyzer_sha256"] = "b" * 64
    assert sha256_payload(payload) != original


def test_negated_free_text_cannot_satisfy_structured_receipt(tmp_path: Path) -> None:
    archive = tmp_path / "protocol.zip"; archive.write_bytes(b"protocol")
    candidate = {"candidate_sha256": "a" * 64, "runtime_tree_sha256": "b" * 64}
    receipt = tmp_path / "receipt.txt"
    receipt.write_text(f"I do not accept candidate {'a' * 64} and do not authorize timestamp or G1", encoding="utf-8")
    with pytest.raises(RuntimeError, match="strict JSON"):
        load_and_validate_receipt(receipt, candidate, archive)


def test_structured_receipt_requires_exact_g1_only_decision(tmp_path: Path) -> None:
    archive = tmp_path / "protocol.zip"; archive.write_bytes(b"protocol")
    candidate = {"candidate_sha256": "a" * 64, "runtime_tree_sha256": "b" * 64}
    payload = {"schema_version": "haxs.stage5c2gR3.1.authorization.v1", "receipt_id": "12345678-1234-5678-1234-567812345678", "decision": "DO_NOT_ACCEPT", "candidate_sha256": "a" * 64, "protocol_archive_sha256": sha256_file(archive), "runtime_tree_sha256": "b" * 64, "authorized_scope": "G1_ONLY", "blocked_scopes": ["G2", "G3", "G4", "STAGE5C3", "STAGE5D", "MANUSCRIPT_RESULT_CLAIMS", "EXACT_MOBILE_HOLE_CLAIMS", "PUBLIC_RELEASE"], "issued_at_utc": "2026-07-17T12:00:00Z", "issuer": {"name": "Supervisor", "role": "SUPERVISOR"}}
    receipt = tmp_path / "receipt.json"; receipt.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RuntimeError, match="decision or scope"):
        load_and_validate_receipt(receipt, candidate, archive)


def _host_attestation(label: str, hardware: str) -> dict:
    transcripts = {name: "1" * 64 for name in ["00_compileall.txt", "01_static_gate.txt", "02_full_tests.txt", "03_targeted_tests.txt", "04_immutable_install.txt", "05_candidate.txt", "06_package.txt", "07_fresh_unzip.txt"]}
    return {"schema_version": "haxs.stage5c2gR3.1.physical-host.v1", "host_label": label, "attested_at_utc": "2026-07-17T12:00:00+00:00", "physical_host": {"platform_uuid_sha256": hardware * 64, "serial_number_sha256": hardware * 64, "system": "Darwin", "machine": "arm64"}, "candidate_sha256": "a" * 64, "runtime_tree_sha256": "b" * 64, "wheel_sha256": "c" * 64, "protocol_archive_sha256": "d" * 64, "canonical_config_hashes": {"G1": "e" * 64}, "expected_plan_hashes": {"G1": "f" * 64}, "environment_spec": {"python": "3.12.7"}, "g0_status": "PASS", "scientific_execution_performed": False, "authoritative_g0_transcript_sha256": transcripts}


def test_two_virtual_environments_on_one_physical_host_are_rejected(tmp_path: Path) -> None:
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    a.write_text(json.dumps(_host_attestation("HOST_A", "1"))); b.write_text(json.dumps(_host_attestation("HOST_B", "1")))
    with pytest.raises(RuntimeError, match="not physically distinct"):
        verify_two_hosts(str(a), str(b))


def test_two_distinct_physical_hosts_preserve_candidate_identity(tmp_path: Path) -> None:
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    a.write_text(json.dumps(_host_attestation("HOST_A", "1"))); b.write_text(json.dumps(_host_attestation("HOST_B", "2")))
    assert verify_two_hosts(str(a), str(b))["status"] == "PASS"


def test_external_copy_wheel_install_does_not_mutate_candidate() -> None:
    dangerous = {"PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP", "PYTHONINSPECT", "PYTHONUSERBASE", "LD_PRELOAD", "DYLD_INSERT_LIBRARIES", "DYLD_LIBRARY_PATH"}
    environment = {key: value for key, value in os.environ.items() if key not in dangerous}
    result = subprocess.run([sys.executable, "-I", "scripts/verify_stage5c2gR3_immutable_install.py"], cwd=ROOT, env=environment, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert '"status": "PASS"' in result.stdout


@pytest.mark.parametrize("script", ["verify_stage5c2gR2_protocol.py", "run_stage5c2gR2_calibration_invariants.py", "run_stage5c2gR3_transport_calibration.py", "run_stage5c2gR3_untouched_validity.py", "run_stage5c2gR3_fixed_count.py"])
def test_rejected_or_blocked_routes_exit_nonzero(script: str) -> None:
    result = subprocess.run([sys.executable, f"scripts/{script}"], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode != 0 and ("REJECTED" in result.stdout + result.stderr or "BLOCKED" in result.stdout + result.stderr)


def test_g2_g3_top_level_redesign_and_coverage_preregistration() -> None:
    g2 = load_yaml("configs/stage5c2gR3/g2_transport.yaml", ROOT)["stage5c2gR3_G2"]; g3 = load_yaml("configs/stage5c2gR3/g3_validity.yaml", ROOT)["stage5c2gR3_G3"]
    assert g2["occupancy_replicates"] >= 16 and g2["paths_per_occupancy"] <= g2["occupancy_replicates"]
    assert g3["hierarchy"]["occupancy_replicates"] >= 16
    assert g3["coverage_calibration"]["minimum_synthetic_datasets_per_grid_cell"] >= 200 and g3["coverage_calibration"]["bootstrap_replicates_per_dataset"] >= 2000
