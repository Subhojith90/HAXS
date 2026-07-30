from __future__ import annotations

import hashlib
import itertools
import json
import os
import tempfile
import uuid
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
R32_CONFIG_ROOT = ROOT / "configs/stage5c2gR32"


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_payload(payload: object) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def atomic_write_json(path: str | Path, payload: object) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=destination.parent, delete=False
    ) as handle:
        temporary = Path(handle.name)
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, destination)


def load_yaml(path: str | Path) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def load_r32_config(name: str) -> dict:
    return load_yaml(R32_CONFIG_ROOT / name)


def stable_uuid(namespace: str, *parts: object) -> str:
    return uuid.uuid5(uuid.UUID(namespace), "|".join(map(str, parts))).hex


def quadrature_initial_spins(
    n_sites: int, holes: list[int], phase_values: list[list[float]]
) -> tuple[np.ndarray, list[dict]]:
    active = [site for site in range(int(n_sites)) if site not in set(map(int, holes))]
    nodes = list(itertools.product(range(len(phase_values)), repeat=len(active)))
    spins = np.zeros((len(nodes), int(n_sites), 3), dtype=float)
    registry: list[dict] = []
    weight = 1.0 / float(len(nodes))
    phase_array = np.asarray(phase_values, dtype=float)
    for node_index, node in enumerate(nodes):
        for active_index, site in enumerate(active):
            spins[node_index, site] = phase_array[node[active_index]]
        registry.append(
            {
                "node_index": node_index,
                "phase_code": "".join(str(value) for value in node),
                "weight": weight,
            }
        )
    return spins, registry


def require_new_output(path: str | Path) -> Path:
    destination = Path(path)
    if destination.exists():
        raise RuntimeError(
            f"refusing to overwrite existing evidence output: {destination}"
        )
    destination.mkdir(parents=True)
    return destination


def file_manifest(root: str | Path) -> dict[str, str]:
    base = Path(root)
    records = {}
    for path in sorted(base.rglob("*")):
        if path.is_symlink():
            raise RuntimeError(f"symlink forbidden in R3.2 evidence: {path}")
        if path.is_file():
            records[path.relative_to(base).as_posix()] = sha256_file(path)
    return records
