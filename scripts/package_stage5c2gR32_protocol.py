#!/usr/bin/env python
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_stage5c2gR32_candidate import build
from stage5c2gR32_common import atomic_write_json, sha256_file, sha256_payload


def _add(archive: zipfile.ZipFile, name: str, data: bytes) -> None:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.external_attr = 0o100644 << 16
    archive.writestr(
        info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9
    )


def main() -> None:
    if len(sys.argv) != 1:
        raise SystemExit("R3.2 packaging accepts no file-selection overrides")
    candidate = build()
    output = ROOT / "output/stage5c2gR32"
    output.mkdir(parents=True, exist_ok=True)
    destination = output / "HAXS_Stage5C2G_R3_2_Protocol.zip"
    prefix = "HAXS_Stage5C2G_R3_2_Protocol"
    compact_evidence = {}
    for gate, record in candidate["pre_candidate_gates"].items():
        paths = [record["path"]]
        if "manifest_path" in record:
            paths.append(record["manifest_path"])
        paths.extend(record.get("supplemental", {}).keys())
        for relative in paths:
            compact_evidence[relative] = sha256_file(ROOT / relative)
    with zipfile.ZipFile(destination, "w") as archive:
        for relative in candidate["runtime_files"]:
            _add(archive, f"{prefix}/{relative}", (ROOT / relative).read_bytes())
        for relative in compact_evidence:
            _add(archive, f"{prefix}/{relative}", (ROOT / relative).read_bytes())
        _add(
            archive,
            f"{prefix}/CANDIDATE.stage5c2gR32.json",
            (json.dumps(candidate, indent=2, sort_keys=True) + "\n").encode(),
        )
        wheel = ROOT / candidate["wheel"]["path"]
        _add(archive, f"{prefix}/{wheel.name}", wheel.read_bytes())
        manifest = {
            **candidate["runtime_files"],
            **compact_evidence,
            wheel.name: candidate["wheel"]["sha256"],
        }
        _add(
            archive,
            f"{prefix}/MANIFEST.stage5c2gR32.json",
            (
                json.dumps(
                    {
                        "files": manifest,
                        "manifest_sha256": sha256_payload(manifest),
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n"
            ).encode(),
        )
    digest = sha256_file(destination)
    sidecar = output / "HAXS_Stage5C2G_R3_2_Protocol_SHA256.txt"
    sidecar.write_text(f"{digest}  {destination.name}\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "PASS",
                "archive": destination.relative_to(ROOT).as_posix(),
                "sha256": digest,
                "candidate_sha256": candidate["candidate_sha256"],
                "next": "TWO_PHYSICALLY_DISTINCT_G0_HOSTS",
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
