#!/usr/bin/env python
from __future__ import annotations

import json
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2gR3_common import CANDIDATE_PATH, INSTALLED_WHEEL_PATH, require_isolated_interpreter, scan_runtime_tree, sha256_file


def add_bytes(archive: zipfile.ZipFile, name: str, data: bytes) -> None:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0)); info.external_attr = 0o100644 << 16
    archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def main() -> None:
    require_isolated_interpreter(ROOT)
    if len(sys.argv) != 1: raise SystemExit("R3 packaging accepts no file-selection overrides")
    candidate_path = ROOT / CANDIDATE_PATH
    if not candidate_path.is_file(): raise SystemExit("run the R3 protocol candidate verifier before packaging")
    candidate = json.loads(candidate_path.read_text(encoding="utf-8")); tree = scan_runtime_tree(ROOT)
    if tree != candidate["runtime_tree"]: raise RuntimeError("runtime tree changed after candidate creation")
    wheel_path = ROOT / INSTALLED_WHEEL_PATH
    if not wheel_path.is_file() or sha256_file(wheel_path) != candidate["installed_wheel"]["wheel_sha256"]: raise RuntimeError("candidate-bound installed wheel is missing or changed")
    output = ROOT / "output/stage5c2gR3"; output.mkdir(parents=True, exist_ok=True)
    destination = output / "HAXS_Stage5C2G_R3_1_Protocol.zip"; prefix = "HAXS_Stage5C2G_R3_1_Protocol"
    manifest_lines = [f"{digest}  {relative}" for relative, digest in tree["files"].items()]
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for relative in tree["files"]: add_bytes(archive, f"{prefix}/{relative}", (ROOT / relative).read_bytes())
        add_bytes(archive, f"{prefix}/MANIFEST.stage5c2gR3_1.sha256", ("\n".join(manifest_lines) + "\n").encode())
        add_bytes(archive, f"{prefix}/CANDIDATE.stage5c2gR3_1.json", candidate_path.read_bytes())
        add_bytes(archive, f"{prefix}/{wheel_path.name}", wheel_path.read_bytes())
        sbom = {"schema": "stage5c2gR3.1.sbom.v1", "candidate_sha256": candidate["candidate_sha256"], "python": candidate["environment"]["observed"]["python"], "platform_system": candidate["environment"]["observed"]["platform_system"], "platform_machine": candidate["environment"]["observed"]["platform_machine"], "distributions": candidate["environment"]["observed"]["packages"], "dependency_lock": candidate["environment"]["lock"], "installed_wheel": candidate["installed_wheel"]}
        add_bytes(archive, f"{prefix}/SBOM.stage5c2gR3_1.json", (json.dumps(sbom, indent=2, sort_keys=True) + "\n").encode())
    sidecar = output / "HAXS_Stage5C2G_R3_1_Protocol_SHA256.txt"; sidecar.write_text(f"{sha256_file(destination)}  {destination.name}\n", encoding="utf-8")
    shutil.copy2(wheel_path, output / wheel_path.name)
    print(json.dumps({"archive": str(destination.relative_to(ROOT)), "sha256": sha256_file(destination), "candidate_sha256": candidate["candidate_sha256"], "runtime_files": len(tree["files"])}, indent=2))


if __name__ == "__main__": main()
