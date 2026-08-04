#!/usr/bin/env python
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import importlib.metadata
import importlib.util
import io
import json
import os
import platform
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2gR32A2_common import load_candidate, sha256_file, sha256_payload, strict_json, verify_record

DANGEROUS_ENVIRONMENT = {
    "PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP", "PYTHONINSPECT", "PYTHONUSERBASE",
    "LD_PRELOAD", "DYLD_INSERT_LIBRARIES", "DYLD_LIBRARY_PATH",
}
PACKAGES = [
    "numpy", "pandas", "scipy", "PyYAML", "matplotlib", "pytest",
    "setuptools", "wheel", "pip",
]
NATIVE_MODULES = ["numpy.core._multiarray_umath", "scipy.linalg._fblas"]
GENERATED_DIST_INFO_NAMES = {"INSTALLER", "REQUESTED", "direct_url.json", "RECORD"}


def _native_identities() -> dict[str, str]:
    identities: dict[str, str] = {}
    for name in NATIVE_MODULES:
        spec = importlib.util.find_spec(name)
        if spec is None or not spec.origin:
            raise RuntimeError(f"required native module unavailable: {name}")
        origin = Path(spec.origin)
        if not origin.is_file() or origin.is_symlink():
            raise RuntimeError(f"unsafe native module origin: {name}")
        identities[name] = sha256_file(origin)
    return identities


def current_environment() -> dict:
    packages = {name: importlib.metadata.version(name) for name in PACKAGES}
    return {
        "implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "python_executable_sha256": sha256_file(sys.executable),
        "platform_system": platform.system(),
        "platform_machine": platform.machine(),
        "packages": packages,
        "native_module_sha256": _native_identities(),
    }


def installed_wheel_tree_identity(target: Path, wheel: Path) -> dict:
    """Verify installed payload bytes without binding pip's absolute source URL."""
    wheel_sha = sha256_file(wheel)
    with zipfile.ZipFile(wheel) as archive:
        members = [item for item in archive.infolist() if not item.is_dir()]
        names = [item.filename for item in members]
        if len(names) != len(set(names)) or any(Path(name).is_absolute() or ".." in Path(name).parts for name in names):
            raise RuntimeError("wheel contains duplicate or unsafe members")
        dist_info = sorted({Path(name).parts[0] for name in names if Path(name).parts[0].endswith(".dist-info")})
        if len(dist_info) != 1:
            raise RuntimeError("wheel must contain exactly one dist-info directory")
        dist_info_name = dist_info[0]
        excluded = {
            f"{dist_info_name}/RECORD",
            f"{dist_info_name}/RECORD.jws",
            f"{dist_info_name}/RECORD.p7s",
        }
        expected = {
            item.filename: hashlib.sha256(archive.read(item.filename)).hexdigest()
            for item in members if item.filename not in excluded
        }

    actual = {
        path.relative_to(target).as_posix(): sha256_file(path)
        for path in sorted(target.rglob("*")) if path.is_file()
    }
    for relative, digest in expected.items():
        installed = target / relative
        if not installed.is_file() or installed.is_symlink() or actual.get(relative) != digest:
            raise RuntimeError(f"installed wheel payload differs from archive: {relative}")
    allowed_generated = {f"{dist_info_name}/{name}" for name in GENERATED_DIST_INFO_NAMES}
    extras = set(actual) - set(expected)
    if not extras.issubset(allowed_generated):
        raise RuntimeError(f"unexpected installed wheel artifact: {sorted(extras-allowed_generated)[:8]}")
    required_generated = {
        f"{dist_info_name}/INSTALLER",
        f"{dist_info_name}/direct_url.json",
        f"{dist_info_name}/RECORD",
    }
    if not required_generated.issubset(actual):
        raise RuntimeError("pip-generated installation metadata is incomplete")
    installer = (target / dist_info_name / "INSTALLER").read_text(encoding="utf-8").strip()
    if installer != "pip":
        raise RuntimeError("unexpected wheel installer metadata")
    direct_url = json.loads((target / dist_info_name / "direct_url.json").read_text(encoding="utf-8"))
    hashes = direct_url.get("archive_info", {}).get("hashes", {})
    legacy_hash = direct_url.get("archive_info", {}).get("hash", "")
    if hashes.get("sha256") != wheel_sha and legacy_hash != f"sha256={wheel_sha}":
        raise RuntimeError("direct_url metadata does not authenticate the bound wheel")

    record_text = (target / dist_info_name / "RECORD").read_text(encoding="utf-8")
    rows = list(csv.reader(io.StringIO(record_text)))
    record = {row[0]: row[1:] for row in rows if len(row) == 3}
    if len(record) != len(rows):
        raise RuntimeError("installed RECORD contains duplicate or malformed rows")
    for relative, digest in expected.items():
        hash_field = record.get(relative, [""])[0]
        if not hash_field.startswith("sha256="):
            raise RuntimeError(f"installed RECORD omits a SHA-256: {relative}")
        encoded = hash_field.split("=", 1)[1]
        decoded = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)).hex()
        if decoded != digest:
            raise RuntimeError(f"installed RECORD hash differs: {relative}")
    return {
        "payload_tree_sha256": sha256_payload(expected),
        "payload_files": len(expected),
        "generated_metadata": sorted(extras),
        "generated_metadata_policy": "validate_installer_record_and_wheel_hash_ignore_absolute_file_url_v1",
    }


def verify_environment(root: Path, candidate: dict | None = None, install_wheel: bool = True) -> dict:
    if not sys.flags.isolated or sys.flags.no_user_site != 1:
        raise RuntimeError("exact-environment verification requires isolated Python (-I)")
    dangerous = sorted(name for name in DANGEROUS_ENVIRONMENT if os.environ.get(name))
    if dangerous:
        raise RuntimeError(f"dangerous import environment present: {dangerous}")
    candidate = candidate or load_candidate(root)
    environment_path = verify_record(root, candidate["environment"], "environment")
    declared = strict_json(environment_path)
    canonical = {key: value for key, value in declared.items() if key != "environment_sha256"}
    if (
        declared.get("schema_version") != "haxs.stage5c2gR32A2.environment.v1"
        or declared.get("environment_sha256") != sha256_payload(canonical)
    ):
        raise RuntimeError("environment attestation self-identity failed")
    observed = current_environment()
    for field, value in observed.items():
        if declared.get(field) != value:
            raise RuntimeError(f"exact environment mismatch: {field}")
    expected_threads = declared.get("thread_environment")
    if not isinstance(expected_threads, dict) or any(os.environ.get(key) != value for key, value in expected_threads.items()):
        raise RuntimeError("exact numerical thread environment mismatch")
    verify_record(root, declared["dependency_lock"], "dependency lock")
    wheelhouse_manifest = verify_record(root, declared["wheelhouse_manifest"], "wheelhouse manifest")
    for line in wheelhouse_manifest.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        artifact = root / relative
        if not artifact.is_file() or artifact.is_symlink() or sha256_file(artifact) != digest:
            raise RuntimeError(f"frozen wheelhouse artifact failed: {relative}")
    wheel = verify_record(root, candidate["wheel"], "installed wheel")
    installed_tree_sha = "NOT_REQUESTED"
    if install_wheel:
        with tempfile.TemporaryDirectory(prefix="haxs-stage5c2gR32A2-preflight-") as directory:
            target = Path(directory) / "site"
            clean = {key: value for key, value in os.environ.items() if key not in DANGEROUS_ENVIRONMENT}
            completed = subprocess.run(
                [sys.executable, "-I", "-m", "pip", "install", "--no-index", "--no-deps", "--no-compile", "--target", str(target), str(wheel)],
                cwd=directory, env=clean, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            )
            if completed.returncode:
                raise RuntimeError("candidate wheel installation failed before attempt reservation")
            installed_identity = installed_wheel_tree_identity(target, wheel)
            installed_tree_sha = installed_identity["payload_tree_sha256"]
            if installed_tree_sha != declared["installed_wheel_tree_sha256"]:
                raise RuntimeError("installed wheel tree identity failed")
            if (
                installed_identity["payload_files"] != declared["installed_wheel_payload_files"]
                or installed_identity["generated_metadata_policy"]
                != declared["generated_install_metadata_policy"]
            ):
                raise RuntimeError("installed wheel metadata policy differs")
            probe = subprocess.run(
                [sys.executable, "-I", "-c", "import json,sys;sys.path.insert(0,sys.argv[1]);import haxs;print(json.dumps({'origin':haxs.__file__,'version':haxs.__version__}))", str(target)],
                cwd=directory, env=clean, text=True, capture_output=True,
            )
            if probe.returncode:
                raise RuntimeError("isolated installed-wheel import failed")
            imported = json.loads(probe.stdout)
            if imported["version"] != declared["haxs_version"] or not Path(imported["origin"]).is_relative_to(target):
                raise RuntimeError("haxs was not imported from the immutable installed wheel")
    return {
        "stage": "stage5c2gR32A2_environment",
        "status": "PASS",
        "candidate_sha256": candidate["candidate_sha256"],
        "environment_sha256": declared["environment_sha256"],
        "installed_wheel_tree_sha256": installed_tree_sha,
        "isolated": True,
        "setup_complete_before_attempt_reservation": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--no-install", action="store_true")
    args = parser.parse_args()
    result = verify_environment(args.root.resolve(), install_wheel=not args.no_install)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
