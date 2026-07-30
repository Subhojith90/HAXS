from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

MOD = 2**63 - 25


def stable_hash(*parts: object, length: int = 32) -> str:
    payload = "|".join(str(part) for part in parts).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:length]


def domain_seed(namespace_uuid: str, block: str, domain: str, *indices: object) -> int:
    """Derive a stable seed from an explicit block/domain namespace."""
    value = int(stable_hash(namespace_uuid, block, domain, *indices, length=16), 16) % MOD
    return value or 1


def config_hash(raw: dict) -> str:
    payload = json.dumps(raw, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def planned_registry(raw: dict) -> pd.DataFrame:
    st = raw["stage5c2f"]
    design = st["design"]
    namespace = str(st["namespace_uuid"])
    labels = list(st["labels"])
    rows = []
    for oi in range(int(design["occupancies"])):
        occupancy_seed = domain_seed(namespace, "primary", "occupancy", oi)
        occupancy_id = stable_hash(namespace, "primary", "occupancy", oi)
        for pj in range(int(design["paths_per_occupancy"])):
            path_seed = domain_seed(namespace, "primary", "path", oi, pj)
            path_id = stable_hash(namespace, "primary", "path", oi, pj)
            for pk in range(int(design["phase_batches_per_path"])):
                phase_seed = domain_seed(namespace, "primary", "phase", oi, pj, pk)
                phase_id = stable_hash(namespace, "primary", "phase", oi, pj, pk)
                for label in labels:
                    rows.append(
                        {
                            "block": "primary",
                            "label": label,
                            "occupancy_idx": oi,
                            "path_idx": pj,
                            "phase_idx": pk,
                            "occupancy_seed": occupancy_seed,
                            "hole_path_seed": path_seed,
                            "phase_batch_seed": phase_seed,
                            "occupancy_realization_id": occupancy_id,
                            "path_realization_id": path_id,
                            "phase_realization_id": phase_id,
                        }
                    )
    return pd.DataFrame(rows)


def sha_array(array) -> str:
    import numpy as np

    return hashlib.sha256(np.asarray(array, dtype=np.int8).tobytes()).hexdigest()


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
