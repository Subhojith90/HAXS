#!/usr/bin/env python3
"""Verify the compact HAXS publication-closure release without dependencies."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
RELEASE_ROOT = ROOT / "publication" / "closure_release_20260903"
CANDIDATE = "481ca1905bedc68d6ac3eb36ac61b80356d4e32cf8847b3e927f081201240932"
PROTOCOL = "d804a203567419f4775fb1d7357cfd9675563ba31068bc10918b9d27f2e1f70f"
G0_SHA = "9745c61a7bbb358472f6d64832af48823686cad1af712e6ddefb3965b6008154"
G1_ATTEMPT = "52e6f14b27a2474ba6db70755825d893"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def load_json(relative: str) -> dict:
    return json.loads((RELEASE_ROOT / relative).read_text(encoding="utf-8"))


def verify_manifest() -> int:
    manifest = RELEASE_ROOT / "MANIFEST_SHA256.txt"
    count = 0
    for number, raw in enumerate(manifest.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        expected, relative = raw.split("  ", 1)
        path = (RELEASE_ROOT / relative).resolve()
        if RELEASE_ROOT.resolve() not in path.parents:
            raise RuntimeError(f"manifest path escapes release at line {number}")
        if not path.is_file() or digest(path) != expected:
            raise RuntimeError(f"release manifest mismatch: {relative}")
        count += 1
    return count


def junit_count(relative: str) -> int:
    root = ET.parse(RELEASE_ROOT / relative).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    tests = sum(int(item.attrib.get("tests", "0")) for item in suites)
    failures = sum(int(item.attrib.get("failures", "0")) for item in suites)
    errors = sum(int(item.attrib.get("errors", "0")) for item in suites)
    skipped = sum(int(item.attrib.get("skipped", "0")) for item in suites)
    if failures or errors or skipped:
        raise RuntimeError(f"non-passing JUnit record: {relative}")
    return tests


def main() -> None:
    release = load_json("RELEASE.json")
    if release["candidate_sha256"] != CANDIDATE:
        raise RuntimeError("release candidate identity mismatch")
    if release["protocol_archive_sha256"] != PROTOCOL:
        raise RuntimeError("release protocol identity mismatch")

    g0 = load_json("evidence/g0/G0_RETURN.json")
    comparison = load_json("evidence/g0/TWO_HOST_G0.json")
    if g0["candidate_sha256"] != CANDIDATE or g0["protocol_archive_sha256"] != PROTOCOL:
        raise RuntimeError("G0 return identity mismatch")
    if g0["return_sha256"] != release["logical_g0_return_sha256"]:
        raise RuntimeError("logical G0 return mismatch")
    if comparison["comparison_sha256"] != G0_SHA:
        raise RuntimeError("two-host comparison identity mismatch")
    if comparison["status"] != "PASS" or not comparison["physically_distinct"]:
        raise RuntimeError("two-host G0 did not pass")
    if comparison["identity_mismatches"] or comparison["forbidden_state"]:
        raise RuntimeError("two-host G0 contains mismatches or forbidden state")
    if comparison["scientific_execution_performed"] or g0["G1_authorized"]:
        raise RuntimeError("G0 scope violation")

    for relative, expected in g0["files"].items():
        if relative == "HAXS_Stage5C2G_R3_2A_5_Protocol.zip":
            continue
        path = RELEASE_ROOT / "evidence" / "g0" / relative
        if digest(path) != expected:
            raise RuntimeError(f"G0 evidence mismatch: {relative}")

    for host in ("HOST_A", "HOST_B"):
        base = f"evidence/g0/evidence/{host}/{host}_junit"
        if junit_count(f"{base}/full_tests.xml") != 402:
            raise RuntimeError(f"{host} full-test count mismatch")
        if junit_count(f"{base}/targeted_tests.xml") != 169:
            raise RuntimeError(f"{host} targeted-test count mismatch")

    state = load_json("evidence/g1/official_return_expanded/control_namespace/state/G1.json")
    manifest = load_json(
        "evidence/g1/official_return_expanded/control_namespace/artifacts/G1/"
        f"{G1_ATTEMPT}/ARTIFACT_MANIFEST.json"
    )
    if state["attempt_id"] != G1_ATTEMPT or state["status"] != "FAILED":
        raise RuntimeError("official G1 terminal state mismatch")
    if state["sequence"] != 1 or state["candidate_sha256"] != CANDIDATE:
        raise RuntimeError("official G1 attempt identity mismatch")
    if manifest["scientific_files"] != {}:
        raise RuntimeError("official G1 unexpectedly contains scientific files")
    if release["g1"]["rerun_authorized"] or release["downstream"]["g2_g4_run"]:
        raise RuntimeError("release improperly authorizes downstream execution")

    gate_table = RELEASE_ROOT / "evidence" / "stage5c2f" / "stage5c2f_gate_table.csv"
    rows = {row["block"]: row for row in csv.DictReader(gate_table.open(newline=""))}
    expected = release["scientific_result"]
    if float(rows["primary"]["mean_effect_db"]) != expected["primary_mean_db"]:
        raise RuntimeError("primary effect mismatch")
    if float(rows["confirmation"]["mean_effect_db"]) != expected["confirmation_mean_db"]:
        raise RuntimeError("confirmation effect mismatch")

    files = verify_manifest()
    print(json.dumps({
        "stage": "haxs_publication_closure_release",
        "status": "PASS",
        "manifest_files": files,
        "candidate_sha256": CANDIDATE,
        "protocol_archive_sha256": PROTOCOL,
        "two_host_g0_sha256": G0_SHA,
        "official_g1_attempt": G1_ATTEMPT,
        "official_g1_status": "FAILED",
        "scientific_files": 0,
        "scientific_execution_performed_by_verifier": False,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"PUBLICATION_CLOSURE_VERIFICATION_FAILED: {error}", file=sys.stderr)
        raise
