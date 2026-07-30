from __future__ import annotations

from pathlib import Path

import pandas as pd

from stage5c2gR2_common import sha256_file, sha256_payload


def deterministic_merge_csv(inputs: list[str | Path], output: str | Path, expected_ids: list[str], id_column: str = "run_id") -> dict:
    paths = sorted((Path(path) for path in inputs), key=lambda path: path.as_posix())
    merged = pd.concat([pd.read_csv(path) for path in paths], ignore_index=True)
    observed = merged[id_column].astype(str).tolist()
    if len(observed) != len(set(observed)): raise RuntimeError("deterministic merge rejected duplicate IDs")
    if sorted(observed) != sorted(map(str, expected_ids)): raise RuntimeError("deterministic merge rejected missing or unexpected IDs")
    merged = merged.sort_values(id_column, kind="mergesort").reset_index(drop=True)
    destination = Path(output); destination.parent.mkdir(parents=True, exist_ok=True); merged.to_csv(destination, index=False)
    return {"path": destination.name, "sha256": sha256_file(destination), "rows": len(merged), "id_column": id_column, "ids_sha256": sha256_payload(sorted(observed))}

