#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import shutil
import stat
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2gR32A2_common import load_candidate, sha256_file, sha256_payload
from stage5c2gR32A2_g0 import finalize_comparison, recompute_two_host_g0

PREFIX = "HAXS_Stage5C2G_R3_2A_2_Complete_G0_Return"


def info(name: str) -> zipfile.ZipInfo:
    item = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    item.external_attr = (stat.S_IFREG | 0o644) << 16
    return item


def copy_clean(source: Path, destination: Path) -> None:
    if not source.is_dir() or source.is_symlink():
        raise RuntimeError(f"host evidence root is missing or unsafe: {source}")
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        if path.is_symlink() or "__pycache__" in relative.parts or path.suffix.lower() in {".pyc", ".pyo", ".pth"}:
            raise RuntimeError(f"forbidden object in host evidence: {relative}")
        target = destination / relative
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif path.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def rebase_host_record(path: Path, prefix: str) -> None:
    host = json.loads(path.read_text(encoding="utf-8"))
    primary = host["primary_evidence"]
    for name in ["full_junit", "targeted_junit", "named_test_ledger"]:
        primary[name]["path"] = f"{prefix}/{primary[name]['path']}"
    for record in primary["transcripts"]:
        record["path"] = f"{prefix}/{record['path']}"
    path.write_text(json.dumps(host, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host-a-root", type=Path, required=True)
    parser.add_argument("--host-b-root", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    candidate = load_candidate()
    protocol = args.protocol.resolve()
    protocol_sha = sha256_file(protocol)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    archive_path = args.out_dir / f"{PREFIX}.zip"
    sidecar = args.out_dir / f"{PREFIX}_SHA256.txt"
    if archive_path.exists() or sidecar.exists():
        raise RuntimeError("refusing to overwrite complete G0 supervisor return")
    with tempfile.TemporaryDirectory(prefix="haxs-stage5c2gR32A2-return-") as directory:
        return_root = Path(directory) / PREFIX
        evidence = return_root / "evidence"
        copy_clean(args.host_a_root.resolve(), evidence / "HOST_A")
        copy_clean(args.host_b_root.resolve(), evidence / "HOST_B")
        host_a = evidence / "HOST_A/HOST_A.json"
        host_b = evidence / "HOST_B/HOST_B.json"
        rebase_host_record(host_a, "evidence/HOST_A")
        rebase_host_record(host_b, "evidence/HOST_B")
        comparison = finalize_comparison(recompute_two_host_g0(host_a, host_b, return_root, candidate))
        comparison_path = return_root / "TWO_HOST_G0.json"
        comparison_path.write_text(json.dumps(comparison, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        shutil.copy2(protocol, return_root / protocol.name)
        files = {
            path.relative_to(return_root).as_posix(): sha256_file(path)
            for path in sorted(return_root.rglob("*")) if path.is_file()
        }
        record = {
            "schema_version": "haxs.stage5c2gR32A2.complete-g0-return.v1",
            "candidate_sha256": candidate["candidate_sha256"],
            "protocol_archive_sha256": protocol_sha,
            "host_a_path": host_a.relative_to(return_root).as_posix(),
            "host_b_path": host_b.relative_to(return_root).as_posix(),
            "comparison_path": comparison_path.relative_to(return_root).as_posix(),
            "files": files, "scientific_execution_performed": False,
            "G1_authorized": False, "return_sha256": "",
        }
        record["return_sha256"] = sha256_payload({key: value for key, value in record.items() if key != "return_sha256"})
        (return_root / "G0_RETURN.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        with zipfile.ZipFile(archive_path, "w", allowZip64=True) as archive:
            for path in sorted(return_root.rglob("*")):
                if path.is_file():
                    archive.writestr(info(path.relative_to(return_root.parent).as_posix()), path.read_bytes(), zipfile.ZIP_DEFLATED, compresslevel=9)
    digest = sha256_file(archive_path)
    sidecar.write_text(f"{digest}  {archive_path.name}\n", encoding="utf-8")
    print(json.dumps({
        "stage": "stage5c2gR32A2_complete_g0_return", "status": "PASS",
        "archive": str(archive_path), "sha256": digest,
        "candidate_sha256": candidate["candidate_sha256"],
        "two_host_g0_sha256": comparison["comparison_sha256"],
        "scientific_execution_performed": False, "G1_authorized": False,
        "next": "SUPERVISORY_REVIEW_NO_RECEIPT_NO_G1",
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
