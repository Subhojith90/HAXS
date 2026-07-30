from __future__ import annotations

import hashlib
import json
import math
import statistics
from pathlib import Path

import numpy as np
import pandas as pd

from stage5c2gR32_common import atomic_write_json, file_manifest, sha256_file, sha256_payload

ROOT = Path(__file__).resolve().parents[1]
COMPONENTS = ("Sx", "Sy", "Sz")


def wilson(successes: int, trials: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if trials <= 0 or not 0 <= successes <= trials:
        raise ValueError("invalid Wilson interval arguments")
    p = successes / trials
    denominator = 1.0 + z * z / trials
    centre = (p + z * z / (2.0 * trials)) / denominator
    radius = z * math.sqrt(p * (1.0 - p) / trials + z * z / (4.0 * trials * trials)) / denominator
    return max(0.0, centre - radius), min(1.0, centre + radius)


def critical_value(alpha: float, family_size: int) -> float:
    if not 0.0 < alpha < 1.0 or family_size < 1:
        raise ValueError("invalid family definition")
    return statistics.NormalDist().inv_cdf(1.0 - alpha / (2.0 * family_size))


def analytic_normal_power(effect: float, standard_error: float, critical: float) -> float:
    if standard_error <= 0.0:
        return float(effect > 0.0)
    return statistics.NormalDist().cdf(effect / standard_error - critical)


def seed(namespace: str, block: str, family_index: int, unit_id: str, method: str) -> int:
    digest = hashlib.sha256(
        f"{namespace}|{block}|{family_index}|{unit_id}|{method}".encode("utf-8")
    ).digest()
    return int.from_bytes(digest[:8], "big") % (2**32 - 1)


def verify_unit_registry(frame: pd.DataFrame) -> list[dict]:
    required = {"unit_id", "case_id", "occupancy_id", "particle_count", "node_count"}
    if set(frame.columns) != required:
        raise RuntimeError("canonical unit registry schema mismatch")
    if len(frame) != 4 or frame["unit_id"].duplicated().any():
        raise RuntimeError("canonical unit registry must contain four unique units")
    expected = {
        ("limit_hopping_zero_chain6", "chain6_hole_2"),
        ("limit_hopping_zero_chain6", "chain6_hole_4"),
        ("limit_spin_density_zero_rect2x3", "rect2x3_hole_2"),
        ("limit_spin_density_zero_rect2x3", "rect2x3_hole_3"),
    }
    observed = set(zip(frame["case_id"].astype(str), frame["occupancy_id"].astype(str)))
    if observed != expected or not (frame["particle_count"].astype(int) == 5).all():
        raise RuntimeError("canonical unit registry content mismatch")
    if not (frame["node_count"].astype(int) == 1024).all():
        raise RuntimeError("canonical unit registry node count mismatch")
    return frame.sort_values(["case_id", "occupancy_id"]).to_dict("records")


def verify_population(frame: pd.DataFrame, units: list[dict]) -> None:
    required = {"unit_id", "case_id", "occupancy_id", "node_index", "time_index", "time", *COMPONENTS}
    if set(frame.columns) != required:
        raise RuntimeError("quadrature population schema mismatch")
    if not np.isfinite(frame.select_dtypes(include=[np.number]).to_numpy(float)).all():
        raise RuntimeError("quadrature population contains invalid numeric values")
    expected_units = {str(unit["unit_id"]) for unit in units}
    if set(frame["unit_id"].astype(str)) != expected_units:
        raise RuntimeError("quadrature population unit coverage mismatch")
    for unit_id, group in frame.groupby("unit_id", sort=True):
        if group.duplicated(["node_index", "time_index"]).any():
            raise RuntimeError(f"duplicate quadrature population cell: {unit_id}")
        nodes = sorted(group["node_index"].astype(int).unique())
        times = sorted(group["time_index"].astype(int).unique())
        if nodes != list(range(1024)) or times != list(range(45)) or len(group) != 1024 * 45:
            raise RuntimeError(f"incomplete quadrature population: {unit_id}")


def sample_counts(method: str, n: int, nodes: int, rng: np.random.Generator) -> np.ndarray:
    if n < 2:
        raise ValueError("sample size must be at least two")
    if method == "iid":
        return rng.multinomial(n, np.full(nodes, 1.0 / nodes)).astype(float)
    if method == "antithetic":
        if n % 2:
            raise ValueError("antithetic sample size must be even")
        draws = rng.integers(0, nodes, size=n // 2)
        counts = np.bincount(
            np.concatenate([draws, (nodes - 1) - draws]), minlength=nodes
        )
        return counts.astype(float)
    if method == "randomized_qmc":
        from scipy.stats import qmc

        if n & (n - 1):
            raise ValueError("randomized QMC requires a power-of-two sample size")
        sampler = qmc.Sobol(d=1, scramble=True, seed=int(rng.integers(0, 2**32 - 1)))
        draws = np.floor(sampler.random_base2(int(math.log2(n)))[:, 0] * nodes).astype(int)
        return np.bincount(draws, minlength=nodes).astype(float)
    raise ValueError(f"unsupported sampling method: {method}")


def sampled_statistics(values: np.ndarray, counts: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    n = float(counts.sum())
    means = counts @ values / n
    second = counts @ (values * values) / n
    variances = np.maximum(0.0, (second - means * means) * n / (n - 1.0))
    return means, np.sqrt(variances / n)


def write_manifest(output: Path, schema: str) -> dict:
    manifest = {"schema_version": schema, "files": file_manifest(output)}
    manifest["manifest_sha256"] = sha256_payload(manifest)
    atomic_write_json(output / "MANIFEST.json", manifest)
    return manifest


def predecessor_identity() -> dict:
    paths = {
        "R3_2_S01": ROOT / "results/stage5c2gR32/S01/verification.json",
        "R3_2_S02": ROOT / "output/stage5c2gR32/g1_preflight/verification.json",
        "R3_2_S03_FAILED": ROOT / "output/stage5c2gR32/sanity_calibration/calibration_decision.json",
        "R3_2_S03_MANIFEST": ROOT / "output/stage5c2gR32/sanity_calibration/MANIFEST.json",
    }
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise RuntimeError(f"predecessor evidence missing: {missing}")
    s03 = json.loads(paths["R3_2_S03_FAILED"].read_text(encoding="utf-8"))
    if s03.get("status") != "FAIL":
        raise RuntimeError("R3.2 S03 must remain a frozen failure")
    return {
        name: {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256_file(path)}
        for name, path in paths.items()
    }
