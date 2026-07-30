#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2gR3_common import require_isolated_interpreter, sha256_file
from stage5c2gR3_state import atomic_write_json
from verify_stage5c2gR3_1_two_physical_hosts import verify_two_hosts

TRANSCRIPTS = ["00_compileall.txt", "01_static_gate.txt", "02_full_tests.txt", "03_targeted_tests.txt", "04_immutable_install.txt", "05_candidate.txt", "06_package.txt", "07_fresh_unzip.txt", "08_host_attestation.txt"]


def _add(archive: zipfile.ZipFile, name: str, source: Path) -> None:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0)); info.external_attr = 0o100644 << 16
    archive.writestr(info, source.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def _transcripts(directory: str) -> list[Path]:
    root = Path(directory)
    paths = [root / name for name in TRANSCRIPTS]
    if any(not path.is_file() or path.is_symlink() or path.stat().st_size == 0 for path in paths):
        raise RuntimeError(f"authoritative transcript set is incomplete: {root}")
    if {path.name for path in root.iterdir() if path.is_file()} != set(TRANSCRIPTS):
        raise RuntimeError(f"authoritative directory contains development or non-final transcripts: {root}")
    return paths


def _verify_transcripts_against_attestation(paths: list[Path], attestation_path: str) -> None:
    payload = json.loads(Path(attestation_path).read_text(encoding="utf-8"))
    expected = payload["authoritative_g0_transcript_sha256"]
    for path in paths[:-1]:
        if expected.get(path.name) != sha256_file(path): raise RuntimeError(f"authoritative transcript changed after host attestation: {path.name}")
    canonical_stdout = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if paths[-1].read_text(encoding="utf-8") != canonical_stdout: raise RuntimeError("host-attestation transcript differs from the attestation JSON")


def main() -> None:
    require_isolated_interpreter(ROOT)
    parser = argparse.ArgumentParser()
    parser.add_argument("--host-a-attestation", required=True); parser.add_argument("--host-b-attestation", required=True)
    parser.add_argument("--host-a-transcripts", required=True); parser.add_argument("--host-b-transcripts", required=True)
    args = parser.parse_args()
    host_gate = verify_two_hosts(args.host_a_attestation, args.host_b_attestation)
    host_a_files, host_b_files = _transcripts(args.host_a_transcripts), _transcripts(args.host_b_transcripts)
    _verify_transcripts_against_attestation(host_a_files, args.host_a_attestation); _verify_transcripts_against_attestation(host_b_files, args.host_b_attestation)
    output = ROOT / "output/stage5c2gR3"; output.mkdir(parents=True, exist_ok=True)
    protocol = output / "HAXS_Stage5C2G_R3_1_Protocol.zip"
    protocol_sidecar = output / "HAXS_Stage5C2G_R3_1_Protocol_SHA256.txt"
    if not protocol.is_file() or not protocol_sidecar.is_file(): raise RuntimeError("R3.1 protocol package and sidecar are required")
    expected = protocol_sidecar.read_text(encoding="utf-8").split()[0]
    if expected != sha256_file(protocol): raise RuntimeError("R3.1 protocol sidecar failed")
    if host_gate["protocol_archive_sha256"] != expected: raise RuntimeError("two-host attestations do not bind the local protocol archive")
    host_gate_path = output / "TWO_PHYSICAL_HOSTS.json"; atomic_write_json(host_gate_path, host_gate)
    destination = output / "HAXS_Stage5C2G_R3_1_Supervisor_Review.zip"; prefix = "HAXS_Stage5C2G_R3_1_Supervisor_Review"
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        _add(archive, f"{prefix}/{protocol.name}", protocol); _add(archive, f"{prefix}/{protocol_sidecar.name}", protocol_sidecar)
        _add(archive, f"{prefix}/TWO_PHYSICAL_HOSTS.json", host_gate_path)
        _add(archive, f"{prefix}/HOST_A/ATTESTATION.json", Path(args.host_a_attestation)); _add(archive, f"{prefix}/HOST_B/ATTESTATION.json", Path(args.host_b_attestation))
        for path in host_a_files: _add(archive, f"{prefix}/HOST_A/transcripts/{path.name}", path)
        for path in host_b_files: _add(archive, f"{prefix}/HOST_B/transcripts/{path.name}", path)
    sidecar = output / "HAXS_Stage5C2G_R3_1_Supervisor_Review_SHA256.txt"
    sidecar.write_text(f"{sha256_file(destination)}  {destination.name}\n", encoding="utf-8")
    print(json.dumps({"stage": "stage5c2gR3_1_supervisor_review_package", "status": "PASS", "archive": str(destination.relative_to(ROOT)), "sha256": sha256_file(destination), "candidate_sha256": host_gate["candidate_sha256"], "authoritative_transcripts_per_host": len(TRANSCRIPTS)}, indent=2))


if __name__ == "__main__": main()
