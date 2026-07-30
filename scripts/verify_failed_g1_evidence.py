#!/usr/bin/env python
from __future__ import annotations

import argparse
import csv
import json
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2gR32_common import (
    atomic_write_json,
    load_r32_config,
    require_new_output,
    sha256_file,
    sha256_payload,
)
from stage5c2gR3_semantics import derive_g1_decision
from stage5c2gR3_semantics_reference import (
    assert_semantic_agreement,
    derive_g1_decision_reference,
)


def _safe_extract(archive: Path, destination: Path) -> None:
    with zipfile.ZipFile(archive) as handle:
        for member in handle.infolist():
            lexical = PurePosixPath(member.filename)
            if (
                lexical.is_absolute()
                or not lexical.parts
                or any(part in {"", ".", ".."} for part in lexical.parts)
            ):
                raise RuntimeError(f"unsafe archive member: {member.filename}")
            mode = member.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise RuntimeError(f"symlink archive member forbidden: {member.filename}")
            target = destination.joinpath(*lexical.parts)
            if target.is_symlink():
                raise RuntimeError(f"pre-existing symlink extraction target: {target}")
        handle.extractall(destination)


def _single(items: list[Path], description: str) -> Path:
    if len(items) != 1:
        raise RuntimeError(f"expected exactly one {description}; observed {len(items)}")
    return items[0]


def _manifest_checks(attempt_root: Path, manifest: dict) -> list[dict]:
    rows = []
    expected_names = {"MANIFEST.json"}
    for role, record in sorted(manifest["files"].items()):
        relative = PurePosixPath(record["path"])
        if relative.is_absolute() or len(relative.parts) != 1:
            raise RuntimeError(f"non-canonical manifest record: {record['path']}")
        path = attempt_root / relative.name
        expected_names.add(relative.name)
        actual_rows = (
            len(pd.read_csv(path))
            if path.suffix == ".csv"
            else len(json.loads(path.read_text(encoding="utf-8")).get("rows", []))
        )
        rows.append(
            {
                "role": role,
                "path": relative.name,
                "expected_sha256": record["sha256"],
                "actual_sha256": sha256_file(path),
                "expected_rows": int(record["rows"]),
                "actual_rows": actual_rows,
                "passed": sha256_file(path) == record["sha256"]
                and actual_rows == int(record["rows"]),
            }
        )
    observed_names = {path.name for path in attempt_root.iterdir() if path.is_file()}
    if observed_names != expected_names:
        raise RuntimeError(
            f"failed evidence tree differs from manifest: {sorted(observed_names ^ expected_names)}"
        )
    if any(path.is_symlink() or path.is_dir() for path in attempt_root.iterdir()):
        raise RuntimeError("failed evidence attempt root contains symlink or nested directory")
    return rows


def verify(archive: Path, expected_sha256: str, out: Path) -> dict:
    specification = load_r32_config("failed_evidence.yaml")[
        "stage5c2gR32_failed_evidence"
    ]
    expected = str(expected_sha256).lower()
    if expected != specification["archive_sha256"]:
        raise RuntimeError("CLI archive digest differs from frozen R3.2 specification")
    actual_archive_sha = sha256_file(archive)
    if actual_archive_sha != expected:
        raise RuntimeError("failed G1 evidence archive SHA-256 mismatch")

    with tempfile.TemporaryDirectory(prefix="stage5c2gR32_S01_") as temporary:
        extraction = Path(temporary)
        _safe_extract(archive, extraction)
        state_path = _single(list(extraction.rglob("results/stage5c2gR3/state/G1.json")), "G1 state")
        package_root = state_path.parents[3]
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if (
            state.get("status") != specification["expected"]["terminal_status"]
            or int(state.get("sequence", -1)) != int(specification["expected"]["sequence"])
            or state.get("attempt_id") != specification["attempt_id"]
            or state.get("candidate_sha256") != specification["candidate_sha256"]
            or state.get("state_sha256") != specification["state_sha256"]
        ):
            raise RuntimeError("terminal failed-state identity differs from frozen S01 specification")
        canonical_state = {key: value for key, value in state.items() if key != "state_sha256"}
        if sha256_payload(canonical_state) != state["state_sha256"]:
            raise RuntimeError("terminal failed-state self digest mismatch")

        attempt_roots = list(
            package_root.glob(
                "results/stage5c2gR3/artifacts/*/*/G1/"
                + specification["attempt_id"]
            )
        )
        attempt_root = _single(attempt_roots, "canonical G1 attempt root")
        manifest_path = attempt_root / "MANIFEST.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest_canonical = {
            key: value for key, value in manifest.items() if key != "manifest_sha256"
        }
        if (
            manifest.get("manifest_sha256") != specification["manifest_sha256"]
            or sha256_payload(manifest_canonical) != manifest["manifest_sha256"]
        ):
            raise RuntimeError("failed-attempt manifest identity mismatch")
        checks = _manifest_checks(attempt_root, manifest)
        if not all(row["passed"] for row in checks):
            raise RuntimeError("one or more failed-attempt manifest records did not verify")

        receipt = package_root / "results/stage5c2gR3/protocol/SUPERVISOR_AUTHORIZATION_G1_ONLY.json"
        if sha256_file(receipt) != specification["receipt_sha256"]:
            raise RuntimeError("frozen G1-only receipt identity mismatch")
        receipt_payload = json.loads(receipt.read_text(encoding="utf-8"))
        if receipt_payload.get("receipt_id") != specification["receipt_id"]:
            raise RuntimeError("frozen G1-only receipt UUID mismatch")

        curves = attempt_root / manifest["files"]["curves"]["path"]
        registry = attempt_root / manifest["files"]["registry"]["path"]
        config_path = package_root / "configs/stage5c2gR3/g1.yaml"
        import yaml

        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        primary = derive_g1_decision(curves, registry, config)
        reference = derive_g1_decision_reference(curves, registry, config)
        assert_semantic_agreement(primary, reference)
        stored = json.loads(
            (attempt_root / manifest["files"]["semantic_decision"]["path"]).read_text(
                encoding="utf-8"
            )
        )
        if stored != primary:
            raise RuntimeError("stored failed semantic decision differs from reconstruction")

        failed_rows = [row for row in primary["rows"] if not row["absolute_sanity_pass"]]
        failed_checks = {
            check
            for row in failed_rows
            for result in row["absolute_sanity"].values()
            for check, passed in result["checks"].items()
            if not passed
        }
        expected_summary = specification["expected"]
        if (
            len(primary["rows"]) != int(expected_summary["comparisons"])
            or sum(row["equality_pass"] for row in primary["rows"])
            != int(expected_summary["equality_passes"])
            or sum(row["absolute_sanity_pass"] for row in primary["rows"])
            != int(expected_summary["absolute_sanity_passes"])
            or len(failed_rows) != int(expected_summary["absolute_sanity_failures"])
            or float(primary["maximum_difference"])
            != float(expected_summary["maximum_difference"])
            or failed_checks != {expected_summary["only_failed_check"]}
        ):
            raise RuntimeError("reconstructed headline decision differs from frozen S01 facts")

        output = require_new_output(out)
        atomic_write_json(output / "regenerated_semantic_decision.json", primary)
        with (output / "manifest_check.csv").open(
            "w", encoding="utf-8", newline=""
        ) as handle:
            writer = csv.DictWriter(handle, fieldnames=list(checks[0]))
            writer.writeheader()
            writer.writerows(checks)
        ledger = {
            "schema_version": "haxs.stage5c2gR32.supersession-ledger.v1",
            "predecessor_candidate_sha256": specification["candidate_sha256"],
            "predecessor_receipt_id": specification["receipt_id"],
            "predecessor_attempt_id": specification["attempt_id"],
            "predecessor_terminal_status": "FAILED",
            "predecessor_result_is_binding": True,
            "same_candidate_retry_forbidden": True,
            "receipt_reuse_forbidden": True,
            "superseding_stage": "stage5c2gR32",
            "supersession_reason": "replace finite-IID boundary predicate with deterministic quadrature; never reinterpret R3.1",
        }
        ledger["ledger_sha256"] = sha256_payload(ledger)
        atomic_write_json(output / "supersession_ledger.json", ledger)
        verification = {
            "schema_version": specification["schema_version"],
            "stage": "S01",
            "status": "PASS",
            "archive_sha256": actual_archive_sha,
            "candidate_sha256": state["candidate_sha256"],
            "receipt_id": specification["receipt_id"],
            "attempt_id": state["attempt_id"],
            "state_sha256": state["state_sha256"],
            "manifest_sha256": manifest["manifest_sha256"],
            "semantic_decision_sha256": primary["decision_sha256"],
            "comparisons": len(primary["rows"]),
            "curve_rows": len(pd.read_csv(curves)),
            "equality_passes": sum(row["equality_pass"] for row in primary["rows"]),
            "absolute_sanity_passes": sum(
                row["absolute_sanity_pass"] for row in primary["rows"]
            ),
            "absolute_sanity_failures": len(failed_rows),
            "only_failed_check": next(iter(failed_checks)),
            "next": "S02_PRE_CANDIDATE_DEVELOPMENT_ONLY",
        }
        atomic_write_json(output / "verification.json", verification)
        output_manifest = {
            path.name: sha256_file(path)
            for path in sorted(output.iterdir())
            if path.is_file() and path.name != "MANIFEST.json"
        }
        atomic_write_json(
            output / "MANIFEST.json",
            {
                "schema_version": "haxs.stage5c2gR32.S01-manifest.v1",
                "files": output_manifest,
                "manifest_sha256": sha256_payload(output_manifest),
            },
        )
        return verification


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument(
        "--out", type=Path, default=ROOT / "results/stage5c2gR32/S01"
    )
    args = parser.parse_args()
    result = verify(args.archive, args.expected_sha256, args.out)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
