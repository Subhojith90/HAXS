#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2gR32A4_common import load_candidate, sha256_file, sha256_payload, strict_json


def copy_tree_clean(source: Path, destination: Path) -> None:
    if destination.exists() or destination.is_symlink():
        raise RuntimeError(f"refusing to overwrite frozen reference: {destination}")
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        if path.is_symlink() or "__pycache__" in relative.parts or path.suffix.lower() in {".pyc", ".pyo", ".pth"}:
            raise RuntimeError(f"unsafe Host-A reference object: {relative}")
        target = destination / relative
        if path.is_dir(): target.mkdir(parents=True, exist_ok=True)
        elif path.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host-a-evidence", type=Path, required=True)
    parser.add_argument("--local-dry-run", type=Path, required=True)
    args = parser.parse_args()
    candidate = load_candidate()
    if args.local_dry_run.is_symlink():
        raise RuntimeError("local dry-run decision must not be symlinked")
    local_dry_run_path = args.local_dry_run.absolute()
    local_dry_run = strict_json(local_dry_run_path)
    if (
        local_dry_run.get("schema_version") != "haxs.stage5c2gR32A4.local-two-host-dry-run.v1"
        or local_dry_run.get("status") != "PASS"
        or local_dry_run.get("candidate_sha256") != candidate["candidate_sha256"]
        or local_dry_run.get("synthetic_dry_run") is not True
        or local_dry_run.get("receipt_eligible") is not False
        or local_dry_run.get("G1_authorized") is not False
        or local_dry_run.get("decision_sha256") != sha256_payload({
            key: value for key, value in local_dry_run.items() if key != "decision_sha256"
        })
    ):
        raise RuntimeError("Host-B release requires the candidate-matched local complete-return gate")
    protocol_dir = ROOT / "output/stage5c2gR32A4"
    release = ROOT / "releases/stage5c2gR32A4"
    reference = ROOT / "ci/frozen/stage5c2gR32A4/reference/HOST_A"
    release.mkdir(parents=True, exist_ok=True)
    for name in ["HAXS_Stage5C2G_R3_2A_4_Protocol.zip", "HAXS_Stage5C2G_R3_2A_4_Protocol_SHA256.txt"]:
        target = release / name
        if target.exists() or target.is_symlink():
            raise RuntimeError(f"refusing to overwrite release object: {target}")
        shutil.copy2(protocol_dir / name, target)
    release_protocol = release / "HAXS_Stage5C2G_R3_2A_4_Protocol.zip"
    if local_dry_run.get("protocol_archive_sha256") != sha256_file(release_protocol):
        raise RuntimeError("local complete-return gate used a different protocol archive")
    copy_tree_clean(args.host_a_evidence.absolute(), reference)
    dry_run_target = ROOT / "ci/frozen/stage5c2gR32A4/reference/LOCAL_TWO_HOST_DRY_RUN.json"
    if dry_run_target.exists() or dry_run_target.is_symlink():
        raise RuntimeError("refusing to overwrite frozen local dry-run decision")
    shutil.copy2(local_dry_run_path, dry_run_target)
    inputs = [
        ROOT / ".github/workflows/stage5c2gR32A4-host-b-g0.yml",
        ROOT / "ci/run_stage5c2gR32A4_g0.sh",
        ROOT / "ci/run_stage5c2gR32A4_github_host_b_g0.sh",
        release / "HAXS_Stage5C2G_R3_2A_4_Protocol.zip",
        release / "HAXS_Stage5C2G_R3_2A_4_Protocol_SHA256.txt",
        dry_run_target,
    ]
    inputs.extend(path for path in reference.rglob("*") if path.is_file())
    wheelhouse = ROOT / "ci/frozen/stage5c2gR32A2/WHEELHOUSE_MANIFEST_SHA256.txt"
    inputs.append(wheelhouse)
    for line in wheelhouse.read_text(encoding="utf-8").splitlines():
        _, relative = line.split("  ", 1)
        inputs.append(ROOT / relative)
    manifest = ROOT / "ci/frozen/stage5c2gR32A4/INPUT_MANIFEST_SHA256.txt"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    if manifest.exists() or manifest.is_symlink():
        raise RuntimeError("refusing to overwrite frozen GitHub input manifest")
    manifest.write_text("".join(
        f"{sha256_file(path)}  {path.relative_to(ROOT).as_posix()}\n" for path in sorted(set(inputs))
    ), encoding="utf-8")
    print(json.dumps({
        "stage": "Stage5C2G-R3.2A.4", "status": "PASS",
        "candidate_sha256": candidate["candidate_sha256"],
        "protocol_archive_sha256": sha256_file(release / "HAXS_Stage5C2G_R3_2A_4_Protocol.zip"),
        "host_b_status": "PENDING", "G1_authorized": False,
        "scientific_execution_performed": False,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
