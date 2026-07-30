from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
MOD = 2**63 - 25
EXCLUDED_PARTS = {".git", ".venv", "__pycache__", ".pytest_cache", "tmp", "output", "results"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_payload(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_yaml(path: str | Path, root: Path = ROOT) -> dict:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = root / candidate
    return yaml.safe_load(candidate.read_text(encoding="utf-8"))


def stable_id(namespace: str, block: str, domain: str, *indices: object) -> str:
    return sha256_payload([namespace, block, domain, *indices])


def domain_seed(namespace: str, block: str, domain: str, *indices: object) -> int:
    value = int(stable_id(namespace, block, domain, *indices)[:16], 16) % MOD
    return value or 1


def physical_random_unit(namespace: str, split: str, case_id: str, occupancy_idx: int, path_idx: int, phase_idx: int) -> dict:
    """Return label-independent identifiers and seeds for one physical random unit."""
    block = f"{split}:{case_id}"
    return {
        "block_id": stable_id(namespace, split, "block", case_id),
        "occupancy_realization_id": stable_id(namespace, block, "occupancy", occupancy_idx),
        "hole_path_realization_id": stable_id(namespace, block, "path", occupancy_idx, path_idx),
        "phase_batch_realization_id": stable_id(namespace, block, "phase", occupancy_idx, path_idx, phase_idx),
        "exact_initial_state_id": stable_id(namespace, block, "exact_initial_state", occupancy_idx),
        "occupancy_seed": domain_seed(namespace, block, "occupancy", occupancy_idx),
        "hole_path_seed": domain_seed(namespace, block, "path", occupancy_idx, path_idx),
        "phase_batch_seed": domain_seed(namespace, block, "phase", occupancy_idx, path_idx, phase_idx),
    }


def scientific_paths(root: Path = ROOT) -> list[Path]:
    """Overinclusive deterministic closure: all local scientific code/config/tests/runbooks."""
    candidates: list[Path] = []
    for directory, patterns in [
        (root / "src/haxs", ["**/*.py"]),
        (root / "scripts", ["*.py"]),
        (root / "scripts_patch", ["**/*.py"]),
        (root / "configs", ["**/*.yaml", "**/*.yml"]),
        (root / "tests", ["**/*.py", "**/*.json", "**/*.yaml"]),
        (root / "docs", ["**/*"]),
    ]:
        for pattern in patterns:
            candidates.extend(directory.glob(pattern) if directory.exists() else [])
    for name in ["pyproject.toml", "requirements.txt", "requirements-stage5c2gR.lock", "STAGE5C2GR_COMMANDS.sh", "README.md"]:
        candidates.append(root / name)
    candidates.extend(root.glob("*.sh"))
    paths = []
    for path in candidates:
        if not path.is_file() or path.suffix in EXCLUDED_SUFFIXES or path.name == ".DS_Store":
            continue
        relative = path.relative_to(root)
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        paths.append(path.resolve())
    return sorted(set(paths))


def custody_mount(root: Path = ROOT, explicit: str | Path | None = None) -> Path:
    if explicit is not None:
        return Path(explicit).resolve()
    return Path(os.environ.get("HAXS_CUSTODY_ROOT", str(root))).resolve()


def verify_custody(protocol: dict, root: Path = ROOT, mount: str | Path | None = None) -> list[dict]:
    config = protocol["stage5c2gR_protocol"]["configs"]["custody"]
    contract = load_yaml(config, root)["stage5c2gR_custody"]
    base = custody_mount(root, mount)
    rows = []
    for item in contract["objects"]:
        path = base / item["logical_path"]
        actual = sha256_file(path) if path.is_file() else "MISSING"
        rows.append({
            "id": str(item["id"]),
            "logical_path": str(item["logical_path"]),
            "expected_sha256": str(item["sha256"]),
            "actual_sha256": actual,
            "passed": actual == str(item["sha256"]),
        })
    return rows


def build_candidate(protocol_path: str | Path = "configs/stage5c2gR/protocol.yaml", root: Path = ROOT, mount: str | Path | None = None) -> dict:
    protocol_file = Path(protocol_path)
    if not protocol_file.is_absolute():
        protocol_file = root / protocol_file
    protocol = load_yaml(protocol_file, root)
    custody = verify_custody(protocol, root, mount)
    failed = [row["id"] for row in custody if not row["passed"]]
    if failed:
        raise RuntimeError(f"content-addressed custody verification failed: {failed}")
    files = {str(path.relative_to(root)): sha256_file(path) for path in scientific_paths(root)}
    stage = protocol["stage5c2gR_protocol"]
    return {
        "stage": "stage5c2gR_protocol_candidate_payload",
        "protocol_version": stage["protocol_version"],
        "protocol_sha256": sha256_file(protocol_file),
        "source_tree_sha256": sha256_payload(files),
        "covered_files": files,
        "custody_contract": load_yaml(stage["configs"]["custody"], root)["stage5c2gR_custody"]["contract"],
        "custody": custody,
        "random_unit_contract": stage["random_unit_contract"],
        "calibration_gates": stage["calibration_gates"],
        "transport_mapping_gates": stage["transport_mapping_gates"],
        "validity_gates": stage["validity_gates"],
        "stop_go_sequence": stage["stop_go_sequence"],
        "forbidden_actions": stage["forbidden_actions"],
    }


def assert_protocol_locked(
    lock_path: str | Path = "results/stage5c2gR/protocol_lock/LOCKED.json",
    protocol_path: str | Path = "configs/stage5c2gR/protocol.yaml",
    root: Path = ROOT,
    mount: str | Path | None = None,
) -> dict:
    lock_file = Path(lock_path)
    if not lock_file.is_absolute():
        lock_file = root / lock_file
    if not lock_file.is_file():
        raise RuntimeError("Stage 5C.2G-R protocol is not externally timestamped and locked")
    lock = json.loads(lock_file.read_text(encoding="utf-8"))
    if lock.get("status") != "LOCKED_WITH_EXTERNAL_TIMESTAMP_RECEIPT":
        raise RuntimeError("Stage 5C.2G-R lock status is not final")
    payload = build_candidate(protocol_path, root, mount)
    candidate_sha = sha256_payload(payload)
    if lock.get("candidate_sha256") != candidate_sha:
        raise RuntimeError("LOCKED.json candidate metadata differs from the reconstructed scientific payload")
    if lock.get("candidate_payload") != payload:
        raise RuntimeError("LOCKED.json payload differs from the reconstructed scientific payload")
    candidate_path = root / lock["candidate_file"]
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    if candidate != {**payload, "candidate_sha256": candidate_sha}:
        raise RuntimeError("stored candidate JSON differs from the reconstructed scientific payload")
    receipt = root / lock["external_timestamp_receipt"]["stored_path"]
    if not receipt.is_file() or sha256_file(receipt) != lock["external_timestamp_receipt"]["sha256"]:
        raise RuntimeError("external timestamp receipt is missing or changed")
    if candidate_sha not in receipt.read_text(encoding="utf-8", errors="replace"):
        raise RuntimeError("external timestamp receipt does not contain the reconstructed candidate SHA-256")
    return lock


def checked_lock(path: str | Path, expected_status: str, protocol_lock: dict, root: Path = ROOT) -> dict:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = root / candidate
    if not candidate.is_file():
        raise RuntimeError(f"required gate lock is missing: {candidate}")
    payload = json.loads(candidate.read_text(encoding="utf-8"))
    if payload.get("status") != expected_status or not payload.get("passed", False):
        raise RuntimeError(f"required gate did not pass: {candidate}")
    if payload.get("protocol_candidate_sha256") != protocol_lock["candidate_sha256"]:
        raise RuntimeError(f"gate lock belongs to another protocol: {candidate}")
    recorded = payload.get("lock_sha256")
    canonical = {key: value for key, value in payload.items() if key != "lock_sha256"}
    if recorded != sha256_payload(canonical):
        raise RuntimeError(f"gate lock payload hash is invalid: {candidate}")
    return payload


def planned_fixed_count_registry(config: dict, hole_count: int) -> pd.DataFrame:
    stage = config["stage5c2gR_fixed_count"]
    namespace = str(stage["namespace_uuid"])
    rows = []
    for occupancy_idx in range(int(stage["occupancies_per_count"])):
        for path_idx in range(int(stage["paths_per_occupancy"])):
            for phase_idx in range(int(stage["phase_batches_per_path"])):
                unit = physical_random_unit(namespace, "fixed_count", f"holes_{int(hole_count):02d}", occupancy_idx, path_idx, phase_idx)
                for label in stage["labels"]:
                    rows.append({"hole_count": int(hole_count), "occupancy_idx": occupancy_idx, "path_idx": path_idx, "phase_idx": phase_idx, "label": label, **unit})
    return pd.DataFrame(rows)


def assert_supervisor_validation_approval(
    approval_path: str | Path,
    protocol_lock: dict,
    validity_gate_path: str | Path = "results/stage5c2gR/validity_analysis/stage5c2gR_validity_gate.json",
    root: Path = ROOT,
) -> dict:
    gate_path = Path(validity_gate_path)
    if not gate_path.is_absolute(): gate_path = root / gate_path
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    if not gate.get("passed") or gate.get("protocol_candidate_sha256") != protocol_lock["candidate_sha256"]:
        raise RuntimeError("fixed-hole production is blocked because untouched validity did not pass")
    approval = Path(approval_path)
    if not approval.is_absolute(): approval = root / approval
    if not approval.is_file():
        raise RuntimeError("fixed-hole production requires a written post-validation supervisor approval receipt")
    text = approval.read_text(encoding="utf-8", errors="replace")
    if protocol_lock["candidate_sha256"] not in text or gate["gate_sha256"] not in text:
        raise RuntimeError("supervisor approval does not bind the current protocol and validity gate")
    return gate
