from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import sys
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
MOD = 2**63 - 25
EXCLUDED_PARTS = {".git", ".venv", "__pycache__", ".pytest_cache", "tmp", "output", "results", "reproducibility", "Archive"}
RUNTIME_SUFFIXES = {".py", ".yaml", ".yml", ".sh", ".toml", ".lock", ".txt", ".md", ".json", ".cfg", ".ini"}
PROTOCOL_PATH = "configs/stage5c2gR2/protocol.yaml"
LOCK_PATH = "results/stage5c2gR2/protocol/LOCKED.json"


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_payload(payload: object) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest()


def load_yaml(path: str | Path, root: Path = ROOT) -> dict:
    candidate = Path(path)
    if not candidate.is_absolute(): candidate = root / candidate
    return yaml.safe_load(candidate.read_text(encoding="utf-8"))


def stable_id(namespace: str, block: str, domain: str, *indices: object) -> str:
    return sha256_payload([namespace, block, domain, *indices])


def domain_seed(namespace: str, block: str, domain: str, *indices: object) -> int:
    value = int(stable_id(namespace, block, domain, *indices)[:16], 16) % MOD
    return value or 1


def physical_unit(namespace: str, gate: str, case_id: str, occupancy_idx: int, path_idx: int, phase_idx: int) -> dict:
    block = f"{gate}:{case_id}"
    return {
        "block_id": stable_id(namespace, gate, "block", case_id),
        "occupancy_realization_id": stable_id(namespace, block, "occupancy", occupancy_idx),
        "hole_path_realization_id": stable_id(namespace, block, "path", occupancy_idx, path_idx),
        "phase_batch_realization_id": stable_id(namespace, block, "phase", occupancy_idx, path_idx, phase_idx),
        "exact_initial_state_id": stable_id(namespace, block, "exact", occupancy_idx),
        "occupancy_seed": domain_seed(namespace, block, "occupancy", occupancy_idx),
        "hole_path_seed": domain_seed(namespace, block, "path", occupancy_idx, path_idx),
        "phase_batch_seed": domain_seed(namespace, block, "phase", occupancy_idx, path_idx, phase_idx),
    }


def discover_runtime_files(root: Path = ROOT) -> list[Path]:
    """Exact runtime-readable/executable set; additions and deletions change candidate identity."""
    paths = []
    for path in root.rglob("*"):
        if not path.is_file() or path.is_symlink() or path.name == ".DS_Store": continue
        relative = path.relative_to(root)
        if any(part in EXCLUDED_PARTS for part in relative.parts): continue
        if path.suffix in {".pyc", ".pyo", ".zip", ".pdf"}: continue
        if path.suffix in RUNTIME_SUFFIXES or path.name.startswith("requirements") or path.name.startswith(".env") or path.name in {"README", "LICENSE"}:
            paths.append(path.resolve())
    return sorted(set(paths))


def environment_spec(root: Path = ROOT) -> dict:
    return load_yaml("configs/stage5c2gR2/environment.yaml", root)["stage5c2gR2_environment"]


def observed_environment() -> dict:
    return {"python": ".".join(map(str, sys.version_info[:3])), "packages": {name: importlib.metadata.version(name) for name in ["numpy", "pandas", "scipy", "matplotlib", "PyYAML", "pytest"]}}


def verify_environment(spec: dict | None = None) -> dict:
    spec = spec or environment_spec()
    observed = observed_environment()
    if sys.version_info[:2] != (3, 12): raise RuntimeError(f"environment identity mismatch: unsupported Python {observed['python']}; expected 3.12.x")
    failed = []
    for package, requirement in spec["packages"].items():
        expected = str(requirement).removeprefix("==")
        if observed["packages"].get(package) != expected: failed.append(f"{package}={observed['packages'].get(package)} expected={expected}")
    if failed: raise RuntimeError("environment identity mismatch: " + "; ".join(failed))
    return observed


def verify_environment_lock_consistency(root: Path = ROOT) -> dict:
    protocol = load_yaml(PROTOCOL_PATH, root)["stage5c2gR2_protocol"]
    spec = environment_spec(root)
    locked = {}
    for line in (root / protocol["environment_lock"]).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"): continue
        name, version = line.split("==", 1); locked[name] = f"=={version}"
    if locked != spec["packages"]: raise RuntimeError("environment lock file differs from canonical environment specification")
    return locked


def plan_g1(config: dict) -> list[dict]:
    stage = config["stage5c2gR2_G1"]; hierarchy = stage["hierarchy"]; rows = []
    for case in stage["cases"]:
        comparison = [label for label in case["labels"] if label != "static_only"][0]
        for occupancy_idx in range(int(hierarchy["occupancy_replicates"])):
            for path_idx in range(int(hierarchy["paths_per_occupancy"])):
                for phase_idx in range(int(hierarchy["phase_batches_per_path"])):
                    unit = physical_unit(stage["namespace_uuid"], "G1", case["id"], occupancy_idx, path_idx, phase_idx)
                    for method in ["exact", "surrogate"]:
                        comparison_id = stable_id(stage["namespace_uuid"], "G1", "comparison", case["id"], occupancy_idx, path_idx, phase_idx, method)
                        rows.append({"comparison_id": comparison_id, "case_id": case["id"], "method": method, "static_label": "static_only", "comparison_label": comparison, "occupancy_idx": occupancy_idx, "path_idx": path_idx, "phase_idx": phase_idx, **unit})
    return rows


def plan_g2(config: dict) -> list[dict]:
    stage = config["stage5c2gR2_G2"]; rows = []
    for case in stage["cases"]:
        for occupancy_idx in range(int(stage["occupancy_replicates"])):
            for eta in stage["eta_grid"]:
                for path_idx in range(int(stage["paths_per_occupancy"])):
                    unit = physical_unit(stage["namespace_uuid"], "G2", case["id"], occupancy_idx, path_idx, 0)
                    rows.append({"run_id": stable_id(stage["namespace_uuid"], "G2", "run", case["id"], occupancy_idx, eta, path_idx), "case_id": case["id"], "occupancy_idx": occupancy_idx, "eta": float(eta), "path_idx": path_idx, **unit})
    return rows


def plan_g3(config: dict) -> list[dict]:
    stage = config["stage5c2gR2_G3"]; h = stage["hierarchy"]; rows = []
    for case in stage["cases"]:
        for occupancy_idx in range(int(h["occupancy_replicates"])):
            for path_idx in range(int(h["paths_per_occupancy"])):
                for phase_idx in range(int(h["phase_batches_per_path"])):
                    unit = physical_unit(stage["namespace_uuid"], "G3", case["id"], occupancy_idx, path_idx, phase_idx)
                    for label in stage["labels"]:
                        rows.append({"run_id": stable_id(stage["namespace_uuid"], "G3", "run", case["id"], occupancy_idx, path_idx, phase_idx, label), "case_id": case["id"], "label": label, "occupancy_idx": occupancy_idx, "path_idx": path_idx, "phase_idx": phase_idx, **unit})
    return rows


def plan_g4(config: dict) -> list[dict]:
    stage = config["stage5c2gR2_G4"]; rows = []
    for holes in stage["fixed_hole_counts"]:
        case_id = f"holes_{int(holes):02d}"
        for occupancy_idx in range(int(stage["occupancies_per_count"])):
            for path_idx in range(int(stage["paths_per_occupancy"])):
                for phase_idx in range(int(stage["phase_batches_per_path"])):
                    unit = physical_unit(stage["namespace_uuid"], "G4", case_id, occupancy_idx, path_idx, phase_idx)
                    for label in stage["labels"]:
                        rows.append({"run_id": stable_id(stage["namespace_uuid"], "G4", "run", holes, occupancy_idx, path_idx, phase_idx, label), "hole_count": int(holes), "label": label, "occupancy_idx": occupancy_idx, "path_idx": path_idx, "phase_idx": phase_idx, **unit})
    return rows


PLAN_BUILDERS = {"G1": plan_g1, "G2": plan_g2, "G3": plan_g3, "G4": plan_g4}


def verify_custody(protocol: dict, root: Path = ROOT, mount: str | Path | None = None) -> list[dict]:
    config = load_yaml(protocol["stage5c2gR2_protocol"]["custody"], root)["stage5c2gR2_custody"]
    base = Path(mount or os.environ.get("HAXS_CUSTODY_ROOT", str(root))).resolve(); rows = []
    for item in config["objects"]:
        path = base / item["logical_path"]; actual = sha256_file(path) if path.is_file() else "MISSING"
        rows.append({"id": item["id"], "logical_path": item["logical_path"], "expected_sha256": item["sha256"], "actual_sha256": actual, "passed": actual == item["sha256"]})
    return rows


def build_candidate(root: Path = ROOT, mount: str | Path | None = None) -> dict:
    protocol = load_yaml(PROTOCOL_PATH, root); stage = protocol["stage5c2gR2_protocol"]
    custody = verify_custody(protocol, root, mount)
    if not all(row["passed"] for row in custody): raise RuntimeError("R2 custody verification failed")
    files = {str(path.relative_to(root)): sha256_file(path) for path in discover_runtime_files(root)}
    configs = {}; plans = {}
    for gate, relative in stage["canonical_configs"].items():
        config = load_yaml(relative, root); plan = PLAN_BUILDERS[gate](config)
        configs[gate] = {"path": relative, "sha256": sha256_file(root / relative)}
        plans[gate] = {"sha256": sha256_payload(plan), "rows": len(plan)}
    env_path = stage["environment"]; locked_packages = verify_environment_lock_consistency(root); env_lock_path = stage["environment_lock"]
    return {"stage": "stage5c2gR2_candidate_payload", "protocol_version": stage["protocol_version"], "protocol_sha256": sha256_file(root / PROTOCOL_PATH), "runtime_file_set": files, "runtime_file_set_sha256": sha256_payload(files), "canonical_configs": configs, "expected_plans": plans, "environment": {"path": env_path, "sha256": sha256_file(root / env_path), "spec": environment_spec(root), "lock_path": env_lock_path, "lock_sha256": sha256_file(root / env_lock_path), "locked_packages": locked_packages}, "custody": custody, "authorization": stage["authorization"], "hierarchical_validity": stage["hierarchical_validity"], "execution_permissions": stage["execution_permissions"], "rejected_candidates": stage["rejected_candidates"]}


def assert_protocol_locked(root: Path = ROOT, mount: str | Path | None = None) -> dict:
    verify_environment(environment_spec(root))
    lock_path = root / LOCK_PATH
    if not lock_path.is_file(): raise RuntimeError("Stage 5C.2G-R2 protocol is not externally timestamped")
    lock = json.loads(lock_path.read_text(encoding="utf-8")); payload = build_candidate(root, mount); candidate_sha = sha256_payload(payload)
    if lock.get("status") != "LOCKED" or lock.get("candidate_sha256") != candidate_sha or lock.get("candidate_payload") != payload: raise RuntimeError("R2 protocol lock differs from reconstructed candidate")
    candidate = json.loads((root / lock["candidate_file"]).read_text(encoding="utf-8"))
    if candidate != {**payload, "candidate_sha256": candidate_sha}: raise RuntimeError("R2 stored candidate differs from reconstruction")
    receipt = root / lock["receipt_path"]
    if not receipt.is_file() or sha256_file(receipt) != lock["receipt_sha256"] or candidate_sha not in receipt.read_text(encoding="utf-8", errors="replace"): raise RuntimeError("R2 external receipt failed")
    return lock


def canonical_config(gate: str, lock: dict, root: Path = ROOT) -> tuple[dict, str, str]:
    identity = lock["candidate_payload"]["canonical_configs"][gate]; path = root / identity["path"]
    if sha256_file(path) != identity["sha256"]: raise RuntimeError(f"canonical {gate} configuration changed")
    config = load_yaml(path, root); plan = PLAN_BUILDERS[gate](config); plan_hash = sha256_payload(plan)
    expected = lock["candidate_payload"]["expected_plans"][gate]
    if plan_hash != expected["sha256"] or len(plan) != expected["rows"]: raise RuntimeError(f"canonical {gate} run plan changed")
    return config, identity["sha256"], plan_hash


def production_label_parameters(label: str, model: dict, overrides: dict | None = None) -> tuple[float, float, float, float]:
    values = dict(model); values.update(overrides or {})
    hopping, eta, coupling = float(values["hopping_t"]), float(values["mobile_eta"]), float(values["lambda_sd"])
    if label == "static_only": return 0.0, 0.0, 0.0, 0.0
    if label == "mobile_only": return hopping, 0.0, eta, 0.0
    if label == "spin_density_only": return 0.0, coupling, 0.0, coupling
    if label in {"combined", "mobile_plus_spin_density"}: return hopping, coupling, eta, coupling
    raise ValueError(f"unknown canonical label: {label}")
