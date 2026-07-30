#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2gR32_common import sha256_file


def _add_file(archive: zipfile.ZipFile, source: Path, name: str) -> None:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.external_attr = 0o100644 << 16
    archive.writestr(
        info,
        source.read_bytes(),
        compress_type=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host-a", required=True, type=Path)
    parser.add_argument("--host-b", required=True, type=Path)
    parser.add_argument("--two-host-comparison", required=True, type=Path)
    args = parser.parse_args()
    comparison = json.loads(args.two_host_comparison.read_text(encoding="utf-8"))
    if comparison.get("status") != "PASS":
        raise RuntimeError("supervisor package is blocked until two-host G0 passes")
    protocol = ROOT / "output/stage5c2gR32/HAXS_Stage5C2G_R3_2_Protocol.zip"
    protocol_sidecar = (
        ROOT / "output/stage5c2gR32/HAXS_Stage5C2G_R3_2_Protocol_SHA256.txt"
    )
    candidate = ROOT / "results/stage5c2gR32/protocol/CANDIDATE.json"
    required = [protocol, protocol_sidecar, candidate, args.host_a, args.host_b, args.two_host_comparison]
    if not all(path.is_file() for path in required):
        raise RuntimeError("R3.2 supervisor-review package inputs are incomplete")
    output = ROOT / "output/stage5c2gR32"
    destination = output / "HAXS_Stage5C2G_R3_2_Supervisor_Review.zip"
    prefix = "HAXS_Stage5C2G_R3_2_Supervisor_Review"
    sources: list[tuple[Path, str]] = [
        (protocol, f"protocol/{protocol.name}"),
        (protocol_sidecar, f"protocol/{protocol_sidecar.name}"),
        (candidate, "candidate/CANDIDATE.json"),
        (args.host_a, "g0/HOST_A.json"),
        (args.host_b, "g0/HOST_B.json"),
        (args.two_host_comparison, "g0/TWO_HOST_G0.json"),
    ]
    for stage_name, directory in [
        ("S01", ROOT / "results/stage5c2gR32/S01"),
        ("S02", ROOT / "output/stage5c2gR32/g1_preflight"),
        ("S03", ROOT / "output/stage5c2gR32/sanity_calibration"),
    ]:
        for path in sorted(directory.rglob("*")):
            if path.is_file():
                sources.append(
                    (path, f"pre_candidate/{stage_name}/{path.relative_to(directory).as_posix()}")
                )
    with zipfile.ZipFile(destination, "w") as archive:
        for source, relative in sources:
            _add_file(archive, source, f"{prefix}/{relative}")
    digest = sha256_file(destination)
    sidecar = output / "HAXS_Stage5C2G_R3_2_Supervisor_Review_SHA256.txt"
    sidecar.write_text(f"{digest}  {destination.name}\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "PASS",
                "archive": destination.relative_to(ROOT).as_posix(),
                "sha256": digest,
                "files": len(sources),
                "scientific_execution_performed": False,
                "next": "SUPERVISORY_ACCEPTANCE_BEFORE_NEW_RECEIPT",
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
