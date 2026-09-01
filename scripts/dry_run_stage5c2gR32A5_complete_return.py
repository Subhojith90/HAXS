#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from finalize_stage5c2gR32A5_authorization import _safe_extract, verify_complete_g0_return
from stage5c2gR32A5_common import (
    atomic_write_json, load_candidate, sha256_file, sha256_payload,
)


def _clean_environment() -> dict[str, str]:
    excluded = {
        "PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP", "PYTHONINSPECT",
        "PYTHONUSERBASE", "LD_PRELOAD", "DYLD_INSERT_LIBRARIES",
        "DYLD_LIBRARY_PATH",
    }
    environment = {key: value for key, value in os.environ.items() if key not in excluded}
    environment.update({
        "PYTHONDONTWRITEBYTECODE": "1", "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
        "VECLIB_MAXIMUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1",
    })
    return environment


def _run_synthetic_host(
    protocol: Path, execution_root: Path, root: Path, label: str,
) -> Path:
    host_record = root / label / f"{label}.json"
    completed = subprocess.run(
        [
            sys.executable, "-I", "-B",
            str(execution_root / "scripts/run_stage5c2gR32A5_g0.py"),
            "--host-label", label, "--protocol", str(protocol), "--out", str(host_record),
        ],
        cwd=execution_root, env=_clean_environment(), text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    transcript = root / f"{label}_PRODUCTION_G0.txt"
    transcript.parent.mkdir(parents=True, exist_ok=True)
    transcript.write_text(completed.stdout, encoding="utf-8")
    if completed.returncode:
        raise RuntimeError(f"synthetic {label} production writer failed:\n{completed.stdout}")
    return host_record.parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if not args.protocol.is_file() or args.protocol.is_symlink():
        raise RuntimeError("local dry run requires one nonsymlink protocol ZIP")
    protocol = args.protocol.absolute()
    out = args.out.resolve()
    if out.exists() or out.is_symlink():
        raise RuntimeError("refusing to overwrite local two-host dry run")
    forbidden = [
        ROOT / "results/stage5c2gR32A5/protocol/AUTHORIZATION.json",
        ROOT / "results/stage5c2gR32A5/protocol/LOCKED.json",
        ROOT / "results/stage5c2gR32A5/protocol/SUPERVISOR_AUTHORIZATION_G1_ONLY.json",
        ROOT / "results/stage5c2gR32A5/state/G1.json",
    ]
    if any(path.exists() or path.is_symlink() for path in forbidden):
        raise RuntimeError("local dry run found authorization, receipt, lock, or G1 state")
    out.mkdir(parents=True)
    hosts = out / "synthetic_hosts"
    with tempfile.TemporaryDirectory(
        prefix="haxs-stage5c2gR32A5-local-protocol-"
    ) as directory:
        with zipfile.ZipFile(protocol) as handle:
            prefix = _safe_extract(handle, Path(directory))
        execution_root = Path(directory) / prefix
        host_a = _run_synthetic_host(protocol, execution_root, hosts, "HOST_A")
        host_b = _run_synthetic_host(protocol, execution_root, hosts, "HOST_B")
    host_b_record = host_b / "HOST_B.json"
    payload = json.loads(host_b_record.read_text(encoding="utf-8"))
    payload["physical_host"]["platform_identity_sha256"] = hashlib.sha256(
        b"R3.2A.5 synthetic dry-run host B platform"
    ).hexdigest()
    payload["physical_host"]["serial_or_node_sha256"] = hashlib.sha256(
        b"R3.2A.5 synthetic dry-run host B serial"
    ).hexdigest()
    host_b_record.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    deliverables = out / "deliverables"
    with tempfile.TemporaryDirectory(
        prefix="haxs-stage5c2gR32A5-local-packager-"
    ) as directory:
        with zipfile.ZipFile(protocol) as handle:
            prefix = _safe_extract(handle, Path(directory))
        packaging_root = Path(directory) / prefix
        completed = subprocess.run(
            [
                sys.executable, "-I", "-B",
                str(packaging_root / "scripts/package_stage5c2gR32A5_supervisor_return.py"),
                "--host-a-root", str(host_a), "--host-b-root", str(host_b),
                "--protocol", str(protocol), "--out-dir", str(deliverables),
                "--synthetic-dry-run",
            ],
            cwd=packaging_root, env=_clean_environment(), text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
    (out / "PACKAGE_COMPLETE_RETURN.txt").write_text(completed.stdout, encoding="utf-8")
    if completed.returncode:
        raise RuntimeError(f"local complete-return packaging failed:\n{completed.stdout}")
    archive = deliverables / "HAXS_Stage5C2G_R3_2A_5_Complete_G0_Return.zip"
    candidate = load_candidate()
    with tempfile.TemporaryDirectory(prefix="haxs-stage5c2gR32A5-local-return-") as directory:
        with zipfile.ZipFile(archive) as handle:
            prefix = _safe_extract(handle, Path(directory))
        comparison, return_sha = verify_complete_g0_return(
            Path(directory) / prefix, candidate, sha256_file(protocol), allow_synthetic=True,
        )
    decision = {
        "schema_version": "haxs.stage5c2gR32A5.local-two-host-dry-run.v1",
        "status": "PASS", "candidate_sha256": candidate["candidate_sha256"],
        "protocol_archive_sha256": sha256_file(protocol),
        "complete_return_archive_sha256": sha256_file(archive),
        "complete_return_sha256": return_sha,
        "two_host_g0_sha256": comparison["comparison_sha256"],
        "synthetic_dry_run": True, "receipt_eligible": False,
        "G1_authorized": False, "scientific_execution_performed": False,
        "decision_sha256": "",
    }
    decision["decision_sha256"] = sha256_payload(
        {key: value for key, value in decision.items() if key != "decision_sha256"}
    )
    atomic_write_json(out / "LOCAL_TWO_HOST_DRY_RUN.json", decision)
    print(json.dumps(decision, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
