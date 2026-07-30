from __future__ import annotations

import contextlib
import fcntl
import json
import os
import tempfile
from pathlib import Path, PurePosixPath

import pandas as pd

from stage5c2gR3_common import PLAN_BUILDERS, ROOT, canonical_config, sha256_file, sha256_payload
from stage5c2gR3_semantics import derive_g1_decision
from stage5c2gR3_semantics_reference import assert_semantic_agreement, derive_g1_decision_reference

REQUIRED_ROLES = {"G1": {"curves", "comparisons", "registry", "attempts", "semantic_decision", "runtime_attestation"}}


def atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def state_path(gate: str, root: Path = ROOT) -> Path:
    return root / f"results/stage5c2gR3/state/{gate}.json"


@contextlib.contextmanager
def exclusive_state_lock(gate: str, root: Path = ROOT):
    lock_path = root / f"results/stage5c2gR3/state/{gate}.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _read_state(gate: str, root: Path = ROOT) -> dict | None:
    path = state_path(gate, root)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def _write_state(gate: str, payload: dict, root: Path = ROOT) -> dict:
    payload = dict(payload)
    payload["state_sha256"] = sha256_payload(payload)
    atomic_write_json(state_path(gate, root), payload)
    return payload


def begin_attempt(gate: str, lock: dict, config_sha: str, plan_sha: str, attempt_id: str, root: Path = ROOT) -> dict:
    with exclusive_state_lock(gate, root):
        previous = _read_state(gate, root)
        if previous and previous.get("status") == "RUNNING":
            raise RuntimeError(f"single-writer gate already has active attempt {previous.get('attempt_id')}")
        sequence = int(previous.get("sequence", 0) if previous else 0) + 1
        return _write_state(gate, {"stage": "stage5c2gR3_single_writer_gate_state", "gate": gate, "status": "RUNNING", "sequence": sequence, "candidate_sha256": lock["candidate_sha256"], "canonical_config_sha256": config_sha, "expected_plan_sha256": plan_sha, "attempt_id": attempt_id, "manifest_path": None, "manifest_sha256": None, "semantic_decision_sha256": None, "error": ""}, root)


def canonical_artifact_root(gate: str, lock: dict, config_sha: str, attempt_id: str, root: Path = ROOT) -> Path:
    if not attempt_id or any(character not in "0123456789abcdef" for character in attempt_id.lower()):
        raise RuntimeError("attempt ID must be non-empty lowercase hexadecimal")
    candidate = Path(os.path.abspath(root)) / "results/stage5c2gR3/artifacts" / lock["candidate_sha256"] / config_sha / gate / attempt_id
    _assert_no_symlink_ancestors(candidate)
    return candidate


def _safe_relative(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise RuntimeError(f"unsafe non-canonical relative artifact path: {value}")
    return path


def _assert_no_symlink_ancestors(path: Path) -> None:
    current = Path(os.path.abspath(path))
    for candidate in [current, *current.parents]:
        if candidate.is_symlink():
            raise RuntimeError(f"symlink forbidden at evidence root or ancestor: {candidate}")


def _assert_no_symlink_chain(path: Path, stop: Path) -> None:
    current = Path(os.path.abspath(path))
    boundary = Path(os.path.abspath(stop))
    if os.path.commonpath([str(current), str(boundary)]) != str(boundary):
        raise RuntimeError("evidence path escaped canonical artifact root")
    while True:
        if current.is_symlink():
            raise RuntimeError(f"symlink forbidden in evidence path: {current}")
        if current == boundary:
            break
        current = current.parent


def assert_canonical_artifact_root(path: Path, repository_root: Path = ROOT) -> None:
    candidate = Path(os.path.abspath(path))
    expected_repository = Path(os.path.abspath(repository_root))
    _assert_no_symlink_ancestors(candidate)
    if os.path.commonpath([str(candidate), str(expected_repository)]) != str(expected_repository):
        raise RuntimeError("canonical artifact root escaped repository root")
    if not candidate.is_dir():
        raise RuntimeError("canonical artifact root is not a directory")
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(candidate, flags)
    except OSError as error:
        raise RuntimeError(f"canonical artifact root no-follow open failed: {candidate}") from error
    else:
        os.close(descriptor)


def build_raw_manifest(gate: str, attempt_root: Path, files: dict[str, Path], expected_ids: list[str], observed_ids: list[str], lock: dict, config_sha: str, plan_sha: str, attempt_id: str, root: Path = ROOT) -> dict:
    canonical_root = canonical_artifact_root(gate, lock, config_sha, attempt_id, root)
    if Path(os.path.abspath(attempt_root)) != Path(os.path.abspath(canonical_root)):
        raise RuntimeError("raw evidence is outside the canonical candidate/config/gate/attempt root")
    assert_canonical_artifact_root(canonical_root, root)
    if sorted(observed_ids) != sorted(expected_ids) or len(observed_ids) != len(set(observed_ids)):
        raise RuntimeError("observed IDs do not equal the unique expected plan")
    if set(files) != REQUIRED_ROLES.get(gate, set(files)):
        raise RuntimeError(f"raw manifest roles differ from canonical {gate} roles")
    records = {}
    for role, path in sorted(files.items()):
        _assert_no_symlink_chain(path, canonical_root)
        if Path(os.path.abspath(path.parent)) != Path(os.path.abspath(canonical_root)) or path.is_symlink():
            raise RuntimeError(f"non-canonical evidence record path: {path}")
        relative = path.relative_to(canonical_root).as_posix()
        _safe_relative(relative)
        if path.suffix == ".csv":
            rows = len(pd.read_csv(path))
        elif path.suffix == ".json":
            content = json.loads(path.read_text(encoding="utf-8"))
            rows = len(content.get("rows", []))
        else:
            raise RuntimeError(f"unsupported evidence record type: {path.name}")
        records[role] = {"path": relative, "sha256": sha256_file(path), "rows": rows}
    payload = {"stage": "stage5c2gR3_recursive_raw_manifest", "gate": gate, "attempt_id": attempt_id, "candidate_sha256": lock["candidate_sha256"], "canonical_config_sha256": config_sha, "expected_plan_sha256": plan_sha, "expected_ids": sorted(expected_ids), "observed_ids": sorted(observed_ids), "files": records}
    payload["manifest_sha256"] = sha256_payload(payload)
    return payload


def verify_raw_manifest(manifest_relative: str | Path, lock: dict, gate: str, attempt_id: str, root: Path = ROOT) -> tuple[dict, Path]:
    supplied = Path(manifest_relative)
    if supplied.is_absolute():
        raise RuntimeError("absolute/external evidence manifest forbidden")
    safe = _safe_relative(supplied.as_posix())
    config, config_sha, plan_sha = canonical_config(gate, lock, root)
    canonical_root = canonical_artifact_root(gate, lock, config_sha, attempt_id, root)
    expected_manifest = canonical_root / "MANIFEST.json"
    manifest_path = root.joinpath(*safe.parts)
    if Path(os.path.abspath(manifest_path)) != Path(os.path.abspath(expected_manifest)):
        raise RuntimeError("manifest is not at the canonical candidate/config/gate/attempt path")
    assert_canonical_artifact_root(canonical_root, root)
    _assert_no_symlink_chain(manifest_path, canonical_root)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    canonical = {key: value for key, value in payload.items() if key != "manifest_sha256"}
    if payload.get("manifest_sha256") != sha256_payload(canonical):
        raise RuntimeError("raw manifest digest failed")
    if payload.get("gate") != gate or payload.get("attempt_id") != attempt_id or payload.get("candidate_sha256") != lock["candidate_sha256"] or payload.get("canonical_config_sha256") != config_sha or payload.get("expected_plan_sha256") != plan_sha:
        raise RuntimeError("raw manifest identity failed")
    identifier = "comparison_id" if gate == "G1" else "run_id"
    canonical_ids = sorted(str(row[identifier]) for row in PLAN_BUILDERS[gate](config))
    if payload.get("expected_ids") != canonical_ids or payload.get("observed_ids") != canonical_ids or len(canonical_ids) != len(set(canonical_ids)):
        raise RuntimeError("raw manifest IDs differ from reconstructed canonical plan")
    if set(payload.get("files", {})) != REQUIRED_ROLES.get(gate, set(payload.get("files", {}))):
        raise RuntimeError("raw manifest required roles failed")
    expected_tree = {"MANIFEST.json"}
    for record in payload["files"].values():
        relative = _safe_relative(str(record["path"]))
        path = canonical_root.joinpath(*relative.parts)
        # Inspect the lexical path before resolving it.  Otherwise an
        # out-of-tree symlink is reported only as an escaping resolved path,
        # obscuring the more specific fail-closed symlink violation.
        _assert_no_symlink_chain(path, canonical_root)
        if Path(os.path.abspath(path.parent)) != Path(os.path.abspath(canonical_root)):
            raise RuntimeError("nested or escaping evidence record forbidden")
        expected_tree.add(relative.as_posix())
        if not path.is_file() or sha256_file(path) != record["sha256"]:
            raise RuntimeError(f"raw artifact changed or missing: {relative}")
        if path.suffix == ".csv" and len(pd.read_csv(path)) != int(record["rows"]):
            raise RuntimeError(f"raw artifact row count changed: {relative}")
    actual_tree = set()
    actual_directories = set()
    for path in canonical_root.rglob("*"):
        if path.is_symlink():
            raise RuntimeError(f"symlink forbidden in recursive evidence tree: {path}")
        if path.is_file():
            actual_tree.add(path.relative_to(canonical_root).as_posix())
        elif path.is_dir():
            actual_directories.add(path.relative_to(canonical_root).as_posix())
    if actual_directories:
        raise RuntimeError(f"recursive evidence tree contains unlisted directories: {sorted(actual_directories)}")
    if actual_tree != expected_tree:
        raise RuntimeError(f"recursive evidence tree differs from manifest: {sorted(actual_tree ^ expected_tree)}")
    return payload, canonical_root


def recompute_g1_semantics(manifest: dict, attempt_root: Path, config: dict) -> dict:
    curves = attempt_root / manifest["files"]["curves"]["path"]
    registry = attempt_root / manifest["files"]["registry"]["path"]
    primary = derive_g1_decision(curves, registry, config)
    reference = derive_g1_decision_reference(curves, registry, config)
    assert_semantic_agreement(primary, reference)
    stored_path = attempt_root / manifest["files"]["semantic_decision"]["path"]
    stored = json.loads(stored_path.read_text(encoding="utf-8"))
    if stored != primary:
        raise RuntimeError("stored semantic decision differs from independent raw-curve recomputation")
    if not primary["passed"]:
        raise RuntimeError(f"G1 scientific authorization predicate failed: equality={primary['equality_passed']} absolute_sanity={primary['absolute_sanity_passed']} maximum={primary['maximum_difference']}")
    return primary


def complete_attempt(gate: str, lock: dict, attempt_id: str, expected_sequence: int, manifest_relative: str, root: Path = ROOT) -> dict:
    with exclusive_state_lock(gate, root):
        current = _read_state(gate, root)
        if not current or current.get("status") != "RUNNING" or current.get("attempt_id") != attempt_id or int(current.get("sequence", -1)) != int(expected_sequence):
            raise RuntimeError("compare-and-swap rejected stale, duplicate, or non-owner completion")
        manifest, attempt_root = verify_raw_manifest(manifest_relative, lock, gate, attempt_id, root)
        config, _, _ = canonical_config(gate, lock, root)
        decision = recompute_g1_semantics(manifest, attempt_root, config) if gate == "G1" else None
        payload = {key: value for key, value in current.items() if key != "state_sha256"}
        payload.update({"status": "PASSED", "manifest_path": manifest_relative, "manifest_sha256": manifest["manifest_sha256"], "semantic_decision_sha256": decision["decision_sha256"] if decision else None, "error": ""})
        return _write_state(gate, payload, root)


def fail_attempt(gate: str, lock: dict, attempt_id: str, expected_sequence: int, error: str, root: Path = ROOT) -> dict:
    with exclusive_state_lock(gate, root):
        current = _read_state(gate, root)
        if not current or current.get("status") != "RUNNING" or current.get("attempt_id") != attempt_id or int(current.get("sequence", -1)) != int(expected_sequence):
            raise RuntimeError("compare-and-swap rejected stale or non-owner failure")
        payload = {key: value for key, value in current.items() if key != "state_sha256"}
        payload.update({"status": "FAILED", "manifest_path": None, "manifest_sha256": None, "semantic_decision_sha256": None, "error": error})
        return _write_state(gate, payload, root)


def verify_gate_state(gate: str, lock: dict, root: Path = ROOT) -> dict:
    state = _read_state(gate, root)
    if not state:
        raise RuntimeError("gate state missing")
    canonical = {key: value for key, value in state.items() if key != "state_sha256"}
    if state.get("state_sha256") != sha256_payload(canonical):
        raise RuntimeError("gate state digest failed")
    if state.get("gate") != gate or state.get("status") != "PASSED" or state.get("candidate_sha256") != lock["candidate_sha256"]:
        raise RuntimeError("latest serialized gate state is not a current PASS")
    config, config_sha, plan_sha = canonical_config(gate, lock, root)
    if state.get("canonical_config_sha256") != config_sha or state.get("expected_plan_sha256") != plan_sha:
        raise RuntimeError("gate state config/plan identity failed")
    manifest, attempt_root = verify_raw_manifest(state["manifest_path"], lock, gate, state["attempt_id"], root)
    if state.get("manifest_sha256") != manifest["manifest_sha256"]:
        raise RuntimeError("gate state does not bind verified raw manifest")
    decision = recompute_g1_semantics(manifest, attempt_root, config) if gate == "G1" else None
    if decision and state.get("semantic_decision_sha256") != decision["decision_sha256"]:
        raise RuntimeError("gate state does not bind recomputed scientific decision")
    return state
