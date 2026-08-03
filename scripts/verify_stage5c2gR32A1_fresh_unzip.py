#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import stat
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from xml.etree.ElementTree import Element, ElementTree, SubElement

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))
from stage5c2gR32A1_authorization import sha256_file, sha256_payload

PREFIX = "HAXS_Stage5C2G_R3_2A_1_Protocol"
EXECUTABLE_SUFFIXES = {".py", ".sh", ".so", ".dylib", ".pyd"}


def _junit(path: Path, status: str, error: str = "") -> None:
    suite = Element(
        "testsuite",
        name="stage5c2gR32A1.strict_root",
        tests="1",
        failures="0" if status == "PASS" else "1",
    )
    case = SubElement(suite, "testcase", name="strict_fresh_unzip_root_closure")
    if status != "PASS":
        failure = SubElement(case, "failure", message=error)
        failure.text = error
    path.parent.mkdir(parents=True, exist_ok=True)
    ElementTree(suite).write(path, encoding="utf-8", xml_declaration=True)


def validate_archive_entries(archive: zipfile.ZipFile) -> list[str]:
    names = archive.namelist()
    if len(names) != len(set(names)):
        raise RuntimeError("duplicate archive entry")
    for item in archive.infolist():
        path = PurePosixPath(item.filename)
        mode = item.external_attr >> 16
        if (
            path.is_absolute()
            or ".." in path.parts
            or stat.S_ISLNK(mode)
            or "__pycache__" in path.parts
            or ".pytest_cache" in path.parts
        ):
            raise RuntimeError(f"unsafe protocol entry: {item.filename}")
        if not path.parts or path.parts[0] != PREFIX:
            raise RuntimeError("protocol archive has an entry outside its exact prefix")
    return names


def validate_strict_root(
    root: Path, candidate: dict, root_manifest: dict
) -> None:
    observed_top = {
        path.name
        for path in root.iterdir()
        if path.name != "BUNDLE_CONTENTS_SHA256.txt"
    }
    allowed_top = set(root_manifest["allowed_top_level_entries"])
    if observed_top != allowed_top:
        raise RuntimeError(
            f"strict root top-level mismatch: "
            f"extra={sorted(observed_top-allowed_top)} "
            f"missing={sorted(allowed_top-observed_top)}"
        )
    for forbidden in root_manifest["forbidden_root_hooks"]:
        if (root / forbidden).exists():
            raise RuntimeError(f"forbidden root hook accepted: {forbidden}")
    symlinks = [
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_symlink()
    ]
    if symlinks:
        raise RuntimeError(f"strict root contains a symlink: {symlinks[:5]}")
    executable_files = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in EXECUTABLE_SUFFIXES
    }
    expected_executables = {
        relative
        for relative in candidate["runtime_files"]
        if Path(relative).suffix.lower() in EXECUTABLE_SUFFIXES
    }
    if executable_files != expected_executables:
        raise RuntimeError("unlisted or missing executable/runtime artifact")


def verify_protocol(protocol: Path, strict_root: bool = True) -> dict:
    if not protocol.is_file() or protocol.is_symlink():
        raise RuntimeError("protocol archive is missing or unsafe")
    with zipfile.ZipFile(protocol) as archive:
        names = validate_archive_entries(archive)
        ledger_name = f"{PREFIX}/BUNDLE_CONTENTS_SHA256.txt"
        if ledger_name not in names:
            raise RuntimeError("checksum ledger missing")
        ledger_lines = archive.read(ledger_name).decode("utf-8").splitlines()
        if any("BUNDLE_CONTENTS_SHA256.txt" in line for line in ledger_lines):
            raise RuntimeError("checksum ledger contains a self-entry")

        with tempfile.TemporaryDirectory(prefix="haxs-r32a1-fresh-") as directory:
            temporary = Path(directory)
            archive.extractall(temporary)
            root = temporary / PREFIX
            expected: dict[str, str] = {}
            for line in ledger_lines:
                digest, relative = line.split("  ", 1)
                if relative in expected:
                    raise RuntimeError("duplicate checksum-ledger path")
                expected[relative] = digest
            actual = {
                path.relative_to(root).as_posix(): sha256_file(path)
                for path in root.rglob("*")
                if path.is_file() and path.name != "BUNDLE_CONTENTS_SHA256.txt"
            }
            if actual != expected:
                raise RuntimeError("fresh-unzip content manifest mismatch")

            candidate_path = (
                root / "results/stage5c2gR32A1/protocol/CANDIDATE.json"
            )
            candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
            canonical_candidate = {
                key: value
                for key, value in candidate.items()
                if key != "candidate_sha256"
            }
            if (
                candidate.get("schema_version")
                != "haxs.stage5c2gR32A1.candidate.v1"
                or candidate.get("candidate_sha256")
                != sha256_payload(canonical_candidate)
            ):
                raise RuntimeError("fresh candidate identity or schema failed")
            if (
                candidate["execution_permissions"]["G1"]
                != "BLOCKED_PENDING_REPLACEMENT_TWO_PHYSICAL_HOST_G0_SUPERVISORY_ACCEPTANCE_AND_NEW_RECEIPT"
            ):
                raise RuntimeError("fresh candidate is not fail closed")

            runtime_actual = {
                relative: sha256_file(root / relative)
                for relative in candidate["runtime_files"]
                if (root / relative).is_file()
                and not (root / relative).is_symlink()
            }
            if runtime_actual != candidate["runtime_files"]:
                raise RuntimeError("candidate runtime is incomplete or changed")
            closure_actual = {
                relative: sha256_file(root / relative)
                for relative in candidate["root_closure_files"]
                if (root / relative).is_file()
                and not (root / relative).is_symlink()
            }
            if closure_actual != candidate["root_closure_files"]:
                raise RuntimeError("candidate root closure is incomplete or changed")
            for name, record in {
                "wheel": candidate["wheel"],
                "environment": candidate["environment"],
                **candidate["authorization_contract"],
            }.items():
                path = root / record["path"]
                if (
                    not path.is_file()
                    or path.is_symlink()
                    or sha256_file(path) != record["sha256"]
                ):
                    raise RuntimeError(
                        f"candidate-bound protocol object failed: {name}"
                    )

            root_manifest_path = (
                root / "results/stage5c2gR32A1/protocol/ROOT_MANIFEST.json"
            )
            root_manifest = json.loads(root_manifest_path.read_text(encoding="utf-8"))
            canonical_manifest = {
                key: value
                for key, value in root_manifest.items()
                if key != "root_manifest_sha256"
            }
            if (
                root_manifest.get("root_manifest_sha256")
                != sha256_payload(canonical_manifest)
                or root_manifest.get("external_root_reconstruction_forbidden")
                is not True
            ):
                raise RuntimeError("root manifest self-identity or policy failed")
            if sha256_file(root_manifest_path) != candidate[
                "authorization_contract"
            ]["root_manifest"]["sha256"]:
                raise RuntimeError("candidate-bound root manifest changed")

            if strict_root:
                validate_strict_root(root, candidate, root_manifest)

            return {
                "stage": "stage5c2gR32A1_fresh_unzip",
                "status": "PASS",
                "candidate_sha256": candidate["candidate_sha256"],
                "protocol_archive_sha256": sha256_file(protocol),
                "content_files": len(expected),
                "strict_root": strict_root,
                "external_root_reconstruction_required": False,
                "G1_authorized": False,
                "scientific_execution_performed": False,
            }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--strict-root", action="store_true", required=True)
    parser.add_argument("--junit", type=Path)
    args = parser.parse_args()
    try:
        result = verify_protocol(args.protocol.resolve(), args.strict_root)
    except Exception as error:
        if args.junit:
            _junit(args.junit, "FAIL", repr(error))
        raise
    if args.junit:
        _junit(args.junit, "PASS")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
