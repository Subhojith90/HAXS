#!/usr/bin/env python
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2gR3_common import INSTALLATION_ATTESTATION_PATH, INSTALLED_WHEEL_PATH, require_isolated_interpreter, scan_runtime_tree, sha256_file, sha256_payload
from stage5c2gR3_state import atomic_write_json


def main() -> None:
    require_isolated_interpreter(ROOT)
    if len(sys.argv) != 1: raise SystemExit("immutable-install check accepts no source/output overrides")
    before = scan_runtime_tree(ROOT); before_sha = sha256_payload(before)
    with tempfile.TemporaryDirectory(prefix="stage5c2gR3_wheel_") as name:
        copied = Path(name) / "source"; wheelhouse = Path(name) / "wheelhouse"; copied.mkdir(); wheelhouse.mkdir()
        for relative in before["directories"]:
            (copied / relative).mkdir(parents=True, exist_ok=True)
        for relative in before["files"]:
            target = copied / relative; target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(ROOT / relative, target)
        dangerous = {"PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP", "PYTHONINSPECT", "PYTHONUSERBASE", "LD_PRELOAD", "DYLD_INSERT_LIBRARIES", "DYLD_LIBRARY_PATH"}
        clean_environment = {key: value for key, value in os.environ.items() if key not in dangerous}
        clean_environment["SOURCE_DATE_EPOCH"] = "315532800"
        completed = subprocess.run([sys.executable, "-I", "-m", "pip", "wheel", "--no-deps", "--no-build-isolation", "--wheel-dir", str(wheelhouse), str(copied)], env=clean_environment, text=True, capture_output=True)
        if completed.returncode != 0: raise RuntimeError("external-copy wheel build failed:\n" + completed.stdout + completed.stderr)
        wheels = list(wheelhouse.glob("haxs-*.whl"))
        if len(wheels) != 1: raise RuntimeError("external-copy build did not produce exactly one HAXS wheel")
        installed = Path(name) / "installed"
        completed = subprocess.run([sys.executable, "-I", "-m", "pip", "install", "--no-deps", "--target", str(installed), str(wheels[0])], env=clean_environment, text=True, capture_output=True)
        if completed.returncode != 0: raise RuntimeError("external wheel installation failed:\n" + completed.stdout + completed.stderr)
        probe_code = "import hashlib,json,pathlib,sys; sys.path.insert(0,sys.argv[1]); import haxs,numpy,pandas,scipy,yaml; mods={'haxs':haxs,'numpy':numpy,'pandas':pandas,'scipy':scipy,'yaml':yaml}; origins={k:str(pathlib.Path(v.__file__).resolve()) for k,v in mods.items()}; native=[]; [native.append((pathlib.Path(m.__file__).name,hashlib.sha256(pathlib.Path(m.__file__).read_bytes()).hexdigest())) for m in list(sys.modules.values()) if getattr(m,'__file__',None) and pathlib.Path(m.__file__).suffix in {'.so','.dylib','.pyd'}]; print(json.dumps({'isolated':bool(sys.flags.isolated),'origins':origins,'sys_path':sys.path,'native_libraries':sorted(set(native))}))"
        completed = subprocess.run([sys.executable, "-I", "-c", probe_code, str(installed)], env=clean_environment, text=True, capture_output=True)
        if completed.returncode != 0: raise RuntimeError("installed external wheel import failed:\n" + completed.stdout + completed.stderr)
        probe = json.loads(completed.stdout)
        haxs_origin = Path(probe["origins"]["haxs"])
        if installed.resolve() not in haxs_origin.parents: raise RuntimeError("HAXS did not import from the isolated installed wheel target")
        installed_files = {path.relative_to(installed).as_posix(): sha256_file(path) for path in sorted((installed / "haxs").rglob("*")) if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}}
        installation_dir = ROOT / Path(INSTALLATION_ATTESTATION_PATH).parent; installation_dir.mkdir(parents=True, exist_ok=True)
        retained_wheel = ROOT / INSTALLED_WHEEL_PATH; shutil.copy2(wheels[0], retained_wheel)
        normalized_native = [{"name": item[0], "sha256": item[1]} for item in probe["native_libraries"]]
        attestation = {"schema_version": "stage5c2gR3.1.installed-wheel.v1", "runtime_tree_sha256": before_sha, "wheel_sha256": sha256_file(retained_wheel), "wheel_filename": retained_wheel.name, "installed_haxs_tree_sha256": sha256_payload(installed_files), "isolated_import_probe": {"isolated": True, "haxs_from_installed_wheel": True, "external_pythonpath_used": False, "module_origin_names": {module: Path(origin).name for module, origin in probe["origins"].items()}}, "native_libraries": normalized_native, "python_executable_sha256": sha256_file(sys.executable)}
        atomic_write_json(ROOT / INSTALLATION_ATTESTATION_PATH, attestation)
    after = scan_runtime_tree(ROOT)
    if after != before: raise RuntimeError("wheel setup mutated the candidate source tree")
    print(json.dumps({"stage": "stage5c2gR3_1_immutable_installed_wheel", "status": "PASS", "candidate_tree_before_sha256": before_sha, "candidate_tree_after_sha256": sha256_payload(after), "wheel_sha256": attestation["wheel_sha256"], "installed_haxs_tree_sha256": attestation["installed_haxs_tree_sha256"], "isolated_import_probe": attestation["isolated_import_probe"]}, indent=2))


if __name__ == "__main__": main()
