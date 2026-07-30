from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
MOD = 2**63 - 25


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_payload(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def stable_id(namespace_uuid: str, block: str, domain: str, *indices: object) -> str:
    return sha256_payload([namespace_uuid, block, domain, *indices])


def domain_seed(namespace_uuid: str, block: str, domain: str, *indices: object) -> int:
    value = int(stable_id(namespace_uuid, block, domain, *indices)[:16], 16) % MOD
    return value or 1


def load_yaml(path: str | Path) -> dict:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    return yaml.safe_load(candidate.read_text(encoding="utf-8"))


def assert_protocol_locked(lock_path: str = "results/stage5c2g/protocol_lock/LOCKED.json") -> dict:
    path = ROOT / lock_path
    if not path.is_file():
        raise RuntimeError("Stage 5C.2G protocol is not finalized. Publish the candidate hash externally and finalize the timestamp receipt before running.")
    lock = json.loads(path.read_text(encoding="utf-8"))
    if lock.get("status") != "LOCKED_WITH_EXTERNAL_TIMESTAMP_RECEIPT":
        raise RuntimeError("Stage 5C.2G protocol lock status is not final")
    for relative, expected in lock["covered_files"].items():
        candidate = ROOT / relative
        if not candidate.is_file() or sha256_file(candidate) != expected:
            raise RuntimeError(f"protocol-covered file changed after lock: {relative}")
    receipt = ROOT / lock["external_timestamp_receipt"]["stored_path"]
    if not receipt.is_file() or sha256_file(receipt) != lock["external_timestamp_receipt"]["sha256"]:
        raise RuntimeError("external timestamp receipt is missing or changed")
    return lock


def planned_fixed_count_registry(config: dict, hole_count: int) -> pd.DataFrame:
    stage = config["stage5c2g_fixed_count"]
    namespace = str(stage["namespace_uuid"])
    rows = []
    for occupancy_idx in range(int(stage["occupancies_per_count"])):
        occupancy_seed = domain_seed(namespace, "fixed_count", "occupancy", hole_count, occupancy_idx)
        occupancy_id = stable_id(namespace, "fixed_count", "occupancy", hole_count, occupancy_idx)
        for path_idx in range(int(stage["paths_per_occupancy"])):
            path_seed = domain_seed(namespace, "fixed_count", "path", hole_count, occupancy_idx, path_idx)
            path_id = stable_id(namespace, "fixed_count", "path", hole_count, occupancy_idx, path_idx)
            for phase_idx in range(int(stage["phase_batches_per_path"])):
                phase_seed = domain_seed(namespace, "fixed_count", "phase", hole_count, occupancy_idx, path_idx, phase_idx)
                phase_id = stable_id(namespace, "fixed_count", "phase", hole_count, occupancy_idx, path_idx, phase_idx)
                for label in stage["labels"]:
                    rows.append({
                        "hole_count": int(hole_count), "label": label,
                        "occupancy_idx": occupancy_idx, "path_idx": path_idx, "phase_idx": phase_idx,
                        "occupancy_seed": occupancy_seed, "hole_path_seed": path_seed, "phase_batch_seed": phase_seed,
                        "occupancy_realization_id": occupancy_id, "path_realization_id": path_id,
                        "phase_realization_id": phase_id,
                    })
    return pd.DataFrame(rows)

