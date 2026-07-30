from __future__ import annotations

import contextlib
import hashlib
import importlib.metadata
import io
import json
import os
import platform
import re
import subprocess
import stat
import sys
import tempfile
from pathlib import Path

import numpy as np
import yaml

import stage5c2gR2_common as r2

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = "configs/stage5c2gR3/protocol.yaml"
LOCK_PATH = "results/stage5c2gR3/protocol/LOCKED.json"
CANDIDATE_PATH = "results/stage5c2gR3/protocol/CANDIDATE.json"
INSTALLATION_ATTESTATION_PATH = "results/stage5c2gR3/installation/ATTESTATION.json"
INSTALLED_WHEEL_PATH = "results/stage5c2gR3/installation/haxs-0.8.1-py3-none-any.whl"
IGNORED_CACHE_DIRS = {"__pycache__", ".pytest_cache"}
ALLOWED_RUNTIME_SUFFIXES = {".py", ".yaml", ".yml", ".json", ".md", ".sh", ".toml", ".txt", ".lock", ".in", ".cfg", ".ini", ".csv"}
FORBIDDEN_RUNTIME_SUFFIXES = {".so", ".pyd", ".dll", ".dylib", ".pth", ".pyc", ".pyo", ".loader"}
FORBIDDEN_RUNTIME_NAMES = {"sitecustomize.py", "usercustomize.py"}


def require_isolated_interpreter(root: Path = ROOT) -> dict:
    stage = protocol(root)
    if not sys.flags.isolated or sys.flags.no_user_site != 1:
        raise RuntimeError("authorization entry point requires Python isolated mode (-I)")
    contaminated = sorted(name for name in stage.get("dangerous_environment_variables", []) if os.environ.get(name))
    if contaminated:
        raise RuntimeError(f"authorization import environment is not scrubbed: {contaminated}")
    return {"isolated": True, "no_user_site": True, "dangerous_environment_variables_present": []}


def assert_execution_root_closed(root: Path = ROOT) -> dict:
    stage = protocol(root)
    allowed = set(stage.get("preparation_root_allowed_entries", []))
    allowed.update(Path(value).parts[0] for value in stage.get("runtime_roots", []))
    allowed.update(Path(value).parts[0] for value in stage.get("runtime_root_files", []))
    allowed.update(stage.get("packaged_root_metadata", []))
    observed = {path.name for path in root.iterdir()}
    unexpected = sorted(observed - allowed)
    forbidden_hooks = sorted(observed & set(stage.get("forbidden_root_hooks", [])))
    unsafe_links = sorted(path.name for path in root.iterdir() if path.is_symlink())
    if unexpected or forbidden_hooks or unsafe_links:
        raise RuntimeError(f"execution root closure failed: unexpected={unexpected} forbidden_hooks={forbidden_hooks} symlinks={unsafe_links}")
    minimal_entries = sorted(set(Path(value).parts[0] for value in [*stage.get("runtime_roots", []), *stage.get("runtime_root_files", [])]))
    return {"policy": "explicit_top_level_deny_by_default_v1", "minimal_execution_entries": minimal_entries, "packaged_metadata": sorted(stage.get("packaged_root_metadata", [])), "forbidden_root_hooks": sorted(stage.get("forbidden_root_hooks", []))}


def assert_official_execution_root_minimal(root: Path = ROOT) -> dict:
    stage = protocol(root)
    required = set(Path(value).parts[0] for value in [*stage.get("runtime_roots", []), *stage.get("runtime_root_files", [])])
    permitted = required | set(stage.get("packaged_root_metadata", [])) | set(stage.get("official_execution_state_entries", []))
    observed = {path.name for path in root.iterdir()}
    if not required <= observed or observed - permitted:
        raise RuntimeError(f"official G1 requires a fresh minimal protocol root: missing={sorted(required - observed)} unexpected={sorted(observed - permitted)}")
    if any(path.is_symlink() for path in root.iterdir()):
        raise RuntimeError("official G1 minimal root contains a symlink")
    return {"policy": "fresh_minimal_protocol_root_v1", "required": sorted(required), "permitted_state_and_metadata": sorted(permitted - required)}


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_payload(payload: object) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def load_yaml(path: str | Path, root: Path = ROOT) -> dict:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = root / candidate
    return yaml.safe_load(candidate.read_text(encoding="utf-8"))


def protocol(root: Path = ROOT) -> dict:
    return load_yaml(PROTOCOL_PATH, root)["stage5c2gR3_protocol"]


def _normalise(gate: str, config: dict) -> dict:
    return {f"stage5c2gR2_{gate}": config[f"stage5c2gR3_{gate}"]}


def plan_g1(config: dict) -> list[dict]:
    return r2.plan_g1(_normalise("G1", config))


def plan_g2(config: dict) -> list[dict]:
    return r2.plan_g2(_normalise("G2", config))


def plan_g3(config: dict) -> list[dict]:
    return r2.plan_g3(_normalise("G3", config))


def plan_g4(config: dict) -> list[dict]:
    return r2.plan_g4(_normalise("G4", config))


PLAN_BUILDERS = {"G1": plan_g1, "G2": plan_g2, "G3": plan_g3, "G4": plan_g4}
physical_unit = r2.physical_unit
production_label_parameters = r2.production_label_parameters


def scan_runtime_tree(root: Path = ROOT) -> dict:
    """Return every authorized runtime path; reject loader/symlink/build-metadata bypasses."""
    stage = protocol(root)
    assert_execution_root_closed(root)
    files: dict[str, str] = {}
    directories: set[str] = set()
    for relative_root in stage["runtime_roots"]:
        base = root / relative_root
        if not base.is_dir():
            raise RuntimeError(f"runtime root missing: {relative_root}")
        directories.add(relative_root)
        for path in sorted(base.rglob("*")):
            relative = path.relative_to(root)
            if any(part in IGNORED_CACHE_DIRS for part in relative.parts):
                continue
            if path.is_symlink():
                raise RuntimeError(f"runtime symlink forbidden: {relative}")
            if any(part.endswith(".egg-info") or part.endswith(".dist-info") for part in relative.parts):
                raise RuntimeError(f"generated package metadata forbidden in candidate tree: {relative}")
            if any(part.startswith(".") for part in relative.parts):
                raise RuntimeError(f"hidden runtime path forbidden: {relative}")
            if path.is_dir():
                directories.add(relative.as_posix())
                continue
            if not path.is_file():
                raise RuntimeError(f"non-regular runtime artifact forbidden: {relative}")
            suffix = path.suffix.lower()
            mode = path.stat().st_mode
            if suffix in FORBIDDEN_RUNTIME_SUFFIXES or path.name in FORBIDDEN_RUNTIME_NAMES:
                raise RuntimeError(f"native/loader runtime artifact forbidden: {relative}")
            if not suffix and mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
                raise RuntimeError(f"extensionless executable forbidden: {relative}")
            if suffix not in ALLOWED_RUNTIME_SUFFIXES:
                raise RuntimeError(f"unknown runtime artifact forbidden: {relative}")
            files[relative.as_posix()] = sha256_file(path)
    for relative in stage["runtime_root_files"]:
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"required root runtime file missing or unsafe: {relative}")
        files[relative] = sha256_file(path)
    return {"files": dict(sorted(files.items())), "directories": sorted(directories)}


def assert_runtime_tree_matches(expected: dict, root: Path = ROOT) -> dict:
    observed = scan_runtime_tree(root)
    if observed != expected:
        expected_files, observed_files = set(expected["files"]), set(observed["files"])
        detail = {
            "added": sorted(observed_files - expected_files),
            "missing": sorted(expected_files - observed_files),
            "changed": sorted(path for path in expected_files & observed_files if expected["files"][path] != observed["files"][path]),
            "directory_set_changed": expected["directories"] != observed["directories"],
        }
        raise RuntimeError(f"exact runtime tree identity failed: {detail}")
    return observed


def environment_spec(root: Path = ROOT) -> dict:
    return load_yaml("configs/stage5c2gR3/environment.yaml", root)["stage5c2gR3_environment"]


def _distribution_record(name: str) -> dict:
    try:
        distribution = importlib.metadata.distribution(name)
    except importlib.metadata.PackageNotFoundError:
        return {"version": "MISSING", "reproducible_content_sha256": "MISSING", "files": 0}
    records = {}
    for item in sorted(distribution.files or [], key=str):
        if ".." in item.parts:
            continue
        # Installer-generated bytecode embeds the absolute installation path
        # in its code object, so it is neither wheel content nor reproducible
        # across clean virtual-environment roots.  Bind the immutable installed
        # sources, native binaries, resources, and stable metadata instead.
        if "__pycache__" in item.parts or item.suffix.lower() in {".pyc", ".pyo"}:
            continue
        if item.name in {"RECORD", "INSTALLER", "REQUESTED", "direct_url.json"}:
            continue
        path = Path(distribution.locate_file(item))
        if path.is_file():
            records[str(item)] = sha256_file(path)
    return {"version": distribution.version, "reproducible_content_sha256": sha256_payload(records), "files": len(records)}


def observed_environment(spec: dict | None = None) -> dict:
    spec = spec or environment_spec()
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        np.show_config()
    threads = {name: os.environ.get(name) for name in spec["numerical_environment"]["required_thread_variables"]}
    distributions = {name: _distribution_record(name) for name in spec["packages"]}
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform_system": platform.system(),
        "platform_machine": platform.machine(),
        "python_executable_sha256": sha256_file(sys.executable),
        "packages": distributions,
        "thread_variables": threads,
        "numpy_config": buffer.getvalue(),
        "numpy_config_sha256": hashlib.sha256(buffer.getvalue().encode()).hexdigest(),
        "numpy_seterr": np.geterr(),
    }


def verify_environment(spec: dict | None = None) -> dict:
    spec = spec or environment_spec()
    observed = observed_environment(spec)
    failures = []
    for key in ["python", "implementation", "platform_system", "platform_machine"]:
        expected = str(spec[key]).removeprefix("==")
        if str(observed[key]) != expected:
            failures.append(f"{key}={observed[key]} expected={expected}")
    for name, requirement in spec["packages"].items():
        expected = str(requirement).removeprefix("==")
        actual = observed["packages"][name]["version"]
        if actual != expected:
            failures.append(f"{name}={actual} expected={expected}")
    for name, expected in spec["numerical_environment"]["required_thread_variables"].items():
        if observed["thread_variables"].get(name) != str(expected):
            failures.append(f"{name}={observed['thread_variables'].get(name)} expected={expected}")
    if not observed["numpy_config"].strip():
        failures.append("BLAS/LAPACK attestation is empty")
    configuration_lower = observed["numpy_config"].lower()
    if "blas" not in configuration_lower or "lapack" not in configuration_lower:
        failures.append("BLAS/LAPACK identity is incomplete")
    if observed["numpy_seterr"] != spec["numerical_environment"]["numpy_seterr"]:
        failures.append(f"numpy_seterr={observed['numpy_seterr']} expected={spec['numerical_environment']['numpy_seterr']}")
    if failures:
        raise RuntimeError("environment identity mismatch: " + "; ".join(failures))
    return observed


def verify_hashed_lock(root: Path = ROOT) -> dict:
    lock = root / protocol(root)["environment_lock"]
    text = lock.read_text(encoding="utf-8")
    if "BOOTSTRAP_REQUIRED" in text or "--hash=sha256:" not in text:
        raise RuntimeError("complete hash-locked R3 dependency file has not been generated")
    locked_versions = {}
    for raw in text.splitlines():
        match = re.match(r"^([A-Za-z0-9_.-]+)==([^ ;\\]+)", raw.strip())
        if match:
            locked_versions[re.sub(r"[-_.]+", "-", match.group(1)).lower()] = match.group(2)
    expected = {re.sub(r"[-_.]+", "-", name).lower(): str(version).removeprefix("==") for name, version in environment_spec(root)["packages"].items()}
    if not set(expected) <= set(locked_versions):
        raise RuntimeError(f"hash lock omits required distributions: {sorted(set(expected) - set(locked_versions))}")
    mismatched = {name: {"expected": version, "locked": locked_versions.get(name)} for name, version in expected.items() if locked_versions.get(name) != version}
    if mismatched:
        raise RuntimeError(f"hash lock versions differ from canonical environment: {mismatched}")
    return {"path": str(lock.relative_to(root)), "sha256": sha256_file(lock), "distributions": dict(sorted(locked_versions.items()))}


def verify_installation_attestation(tree: dict, root: Path = ROOT) -> dict:
    attestation_path = root / INSTALLATION_ATTESTATION_PATH
    wheel_path = root / INSTALLED_WHEEL_PATH
    if not attestation_path.is_file() or attestation_path.is_symlink() or not wheel_path.is_file() or wheel_path.is_symlink():
        raise RuntimeError("isolated installed-wheel attestation is missing; run the immutable-install gate first")
    payload = json.loads(attestation_path.read_text(encoding="utf-8"))
    required = {"schema_version", "runtime_tree_sha256", "wheel_sha256", "wheel_filename", "installed_haxs_tree_sha256", "isolated_import_probe", "native_libraries", "python_executable_sha256"}
    if set(payload) != required or payload.get("schema_version") != "stage5c2gR3.1.installed-wheel.v1":
        raise RuntimeError("installed-wheel attestation schema failed")
    if payload.get("runtime_tree_sha256") != sha256_payload(tree):
        raise RuntimeError("installed-wheel attestation does not bind the current runtime tree")
    if payload.get("wheel_sha256") != sha256_file(wheel_path) or payload.get("wheel_filename") != wheel_path.name:
        raise RuntimeError("installed-wheel hash or filename failed")
    probe = payload.get("isolated_import_probe", {})
    if probe.get("isolated") is not True or probe.get("haxs_from_installed_wheel") is not True or probe.get("external_pythonpath_used") is not False:
        raise RuntimeError("installed-wheel isolated import probe failed")
    dangerous = set(protocol(root).get("dangerous_environment_variables", []))
    clean_environment = {key: value for key, value in os.environ.items() if key not in dangerous}
    with tempfile.TemporaryDirectory(prefix="stage5c2gR3_1_recompute_wheel_") as name:
        installed = Path(name) / "installed"; installed.mkdir()
        completed = subprocess.run([sys.executable, "-I", "-m", "pip", "install", "--no-deps", "--target", str(installed), str(wheel_path)], env=clean_environment, text=True, capture_output=True)
        if completed.returncode != 0: raise RuntimeError("candidate verifier could not independently install the bound wheel:\n" + completed.stdout + completed.stderr)
        probe_code = "import hashlib,json,pathlib,sys; sys.path.insert(0,sys.argv[1]); import haxs,numpy,pandas,scipy,yaml; mods={'haxs':haxs,'numpy':numpy,'pandas':pandas,'scipy':scipy,'yaml':yaml}; origins={k:str(pathlib.Path(v.__file__).resolve()) for k,v in mods.items()}; native=[]; [native.append((pathlib.Path(m.__file__).name,hashlib.sha256(pathlib.Path(m.__file__).read_bytes()).hexdigest())) for m in list(sys.modules.values()) if getattr(m,'__file__',None) and pathlib.Path(m.__file__).suffix in {'.so','.dylib','.pyd'}]; print(json.dumps({'isolated':bool(sys.flags.isolated),'origins':origins,'sys_path':sys.path,'native_libraries':sorted(set(native))}))"
        completed = subprocess.run([sys.executable, "-I", "-c", probe_code, str(installed)], env=clean_environment, text=True, capture_output=True)
        if completed.returncode != 0: raise RuntimeError("candidate verifier installed-wheel import probe failed:\n" + completed.stdout + completed.stderr)
        observed_probe = json.loads(completed.stdout)
        haxs_origin = Path(observed_probe["origins"]["haxs"])
        if installed.resolve() not in haxs_origin.parents: raise RuntimeError("candidate verifier did not import HAXS from the bound wheel")
        installed_files = {path.relative_to(installed).as_posix(): sha256_file(path) for path in sorted((installed / "haxs").rglob("*")) if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}}
        recomputed_tree_sha = sha256_payload(installed_files)
        recomputed_native = [{"name": item[0], "sha256": item[1]} for item in observed_probe["native_libraries"]]
        recomputed_names = {module: Path(origin).name for module, origin in observed_probe["origins"].items()}
    if payload.get("installed_haxs_tree_sha256") != recomputed_tree_sha or payload.get("native_libraries") != recomputed_native or probe.get("module_origin_names") != recomputed_names or payload.get("python_executable_sha256") != sha256_file(sys.executable):
        raise RuntimeError("installed-wheel attestation differs from independent installation/import recomputation")
    return payload


def verify_custody(root: Path = ROOT, mount: str | Path | None = None) -> list[dict]:
    config = load_yaml(protocol(root)["custody"], root)["stage5c2gR3_custody"]
    base = Path(mount or os.environ.get("HAXS_CUSTODY_ROOT", str(root))).resolve()
    rows = []
    for item in config["objects"]:
        path = base / item["logical_path"]
        actual = sha256_file(path) if path.is_file() else "MISSING"
        rows.append({**item, "actual_sha256": actual, "passed": actual == item["sha256"]})
    return rows


def build_candidate(root: Path = ROOT, mount: str | Path | None = None, enforce_environment: bool = True) -> dict:
    stage = protocol(root)
    custody = verify_custody(root, mount)
    if not all(row["passed"] for row in custody):
        raise RuntimeError("R3 predecessor custody verification failed")
    tree = scan_runtime_tree(root)
    configs, plans = {}, {}
    for gate, relative in stage["canonical_configs"].items():
        config = load_yaml(relative, root)
        plan = PLAN_BUILDERS[gate](config)
        configs[gate] = {"path": relative, "sha256": sha256_file(root / relative)}
        plans[gate] = {"sha256": sha256_payload(plan), "rows": len(plan)}
    environment = verify_environment(environment_spec(root)) if enforce_environment else observed_environment(environment_spec(root))
    semantic = {name: {"path": path, "sha256": sha256_file(root / path)} for name, path in stage["semantic_analyzers"].items()}
    return {
        "stage": "stage5c2gR3_candidate_payload",
        "protocol_version": stage["protocol_version"],
        "protocol_sha256": sha256_file(root / PROTOCOL_PATH),
        "runtime_tree": tree,
        "runtime_tree_sha256": sha256_payload(tree),
        "execution_root_policy": assert_execution_root_closed(root),
        "canonical_configs": configs,
        "expected_plans": plans,
        "semantic_analyzers": semantic,
        "environment": {"spec": environment_spec(root), "observed": environment, "lock": verify_hashed_lock(root)},
        "installed_wheel": verify_installation_attestation(tree, root),
        "custody": custody,
        "authorization": stage["authorization"],
        "execution_permissions": stage["execution_permissions"],
        "rejected_candidates": stage["rejected_candidates"],
    }


def assert_protocol_locked(root: Path = ROOT, mount: str | Path | None = None) -> dict:
    lock_path = root / LOCK_PATH
    if not lock_path.is_file():
        raise RuntimeError("Stage 5C.2G-R3.1 is not supervisor-accepted under an exact structured receipt")
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    assert_official_execution_root_minimal(root)
    payload = build_candidate(root, mount)
    candidate_sha = sha256_payload(payload)
    if lock.get("status") != "LOCKED_G1_ONLY" or lock.get("authorized_scope") != "G1_ONLY" or lock.get("candidate_sha256") != candidate_sha or lock.get("candidate_payload") != payload:
        raise RuntimeError("R3 protocol lock differs from complete reconstruction")
    assert_runtime_tree_matches(payload["runtime_tree"], root)
    receipt = root / lock["receipt_path"]
    archive = Path(lock["protocol_archive_path"])
    if not receipt.is_file() or sha256_file(receipt) != lock["receipt_sha256"] or not archive.is_file() or sha256_file(archive) != lock.get("protocol_archive_sha256"):
        raise RuntimeError("R3 external receipt failed")
    from stage5c2gR3_receipt import load_and_validate_receipt
    structured = load_and_validate_receipt(receipt, {**payload, "candidate_sha256": candidate_sha}, archive)
    if structured["receipt_id"] != lock.get("receipt_id"):
        raise RuntimeError("R3 structured receipt ID differs from lock")
    return lock


def canonical_config(gate: str, lock: dict, root: Path = ROOT) -> tuple[dict, str, str]:
    identity = lock["candidate_payload"]["canonical_configs"][gate]
    path = root / identity["path"]
    if sha256_file(path) != identity["sha256"]:
        raise RuntimeError(f"canonical {gate} configuration changed")
    config = load_yaml(path, root)
    plan = PLAN_BUILDERS[gate](config)
    plan_sha = sha256_payload(plan)
    expected = lock["candidate_payload"]["expected_plans"][gate]
    if plan_sha != expected["sha256"] or len(plan) != expected["rows"]:
        raise RuntimeError(f"canonical {gate} run plan changed")
    return config, identity["sha256"], plan_sha
