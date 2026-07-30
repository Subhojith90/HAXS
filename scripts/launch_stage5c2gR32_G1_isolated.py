#!/usr/bin/env python
from __future__ import annotations

import json
import os
import secrets
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2gR32_common import atomic_write_json, sha256_file, sha256_payload


def _candidate() -> dict:
    records = [
        path
        for path in [
            ROOT / "CANDIDATE.stage5c2gR32.json",
            ROOT / "results/stage5c2gR32/protocol/CANDIDATE.json",
        ]
        if path.is_file()
    ]
    if len(records) != 1:
        raise RuntimeError("expected exactly one candidate record")
    return json.loads(records[0].read_text(encoding="utf-8"))


def main() -> None:
    if not sys.flags.isolated or sys.flags.no_user_site != 1:
        raise RuntimeError("official R3.2 G1 requires Python isolated mode (-I)")
    if len(sys.argv) != 1:
        raise SystemExit("official R3.2 G1 accepts no overrides")
    state_path = ROOT / "results/stage5c2gR32/state/G1.json"
    if state_path.exists():
        raise RuntimeError("official R3.2 G1 has already been attempted; retry forbidden")
    candidate = _candidate()
    lock_path = ROOT / "results/stage5c2gR32/protocol/LOCKED.json"
    if not lock_path.is_file():
        raise RuntimeError("official R3.2 G1 is blocked pending a new structured receipt")
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    canonical_lock = {key: value for key, value in lock.items() if key != "lock_sha256"}
    if (
        lock.get("lock_sha256") != sha256_payload(canonical_lock)
        or lock.get("status") != "LOCKED_G1_ONLY"
        or lock.get("authorized_scope") != "G1_ONLY"
        or lock.get("candidate_sha256") != candidate["candidate_sha256"]
        or lock.get("official_attempt_limit") != 1
        or lock.get("same_candidate_retry_forbidden") is not True
    ):
        raise RuntimeError("official R3.2 lock identity or scope failed")
    receipt = ROOT / lock["receipt_path"]
    if not receipt.is_file() or sha256_file(receipt) != lock["receipt_sha256"]:
        raise RuntimeError("official R3.2 structured receipt changed or is missing")
    wheel = ROOT / candidate["wheel"]["path"]
    if not wheel.is_file():
        wheel = ROOT / Path(candidate["wheel"]["path"]).name
    if sha256_file(wheel) != candidate["wheel"]["sha256"]:
        raise RuntimeError("official R3.2 wheel identity failed")

    attempt_id = uuid.uuid4().hex
    output = (
        ROOT
        / "results/stage5c2gR32/artifacts"
        / candidate["candidate_sha256"]
        / "G1"
        / attempt_id
    )
    state_path.parent.mkdir(parents=True, exist_ok=True)
    running = {
        "schema_version": "haxs.stage5c2gR32.single-attempt-state.v1",
        "gate": "G1",
        "status": "RUNNING",
        "sequence": 1,
        "attempt_id": attempt_id,
        "candidate_sha256": candidate["candidate_sha256"],
        "receipt_id": lock["receipt_id"],
        "artifact_path": output.relative_to(ROOT).as_posix(),
        "error": "",
    }
    running["state_sha256"] = sha256_payload(running)
    atomic_write_json(state_path, running)
    environment = {
        key: value
        for key, value in os.environ.items()
        if key
        not in {
            "PYTHONPATH",
            "PYTHONHOME",
            "PYTHONSTARTUP",
            "PYTHONINSPECT",
            "PYTHONUSERBASE",
            "LD_PRELOAD",
            "DYLD_INSERT_LIBRARIES",
            "DYLD_LIBRARY_PATH",
        }
    }
    try:
        with tempfile.TemporaryDirectory(prefix="stage5c2gR32_official_G1_") as name:
            installed = Path(name) / "installed"
            installed.mkdir()
            completed = subprocess.run(
                [
                    sys.executable,
                    "-I",
                    "-m",
                    "pip",
                    "install",
                    "--no-deps",
                    "--target",
                    str(installed),
                    str(wheel),
                ],
                cwd=ROOT,
                env=environment,
                text=True,
            )
            if completed.returncode != 0:
                raise RuntimeError("candidate-bound wheel installation failed")
            environment["HAXS_R32_INSTALLED_TARGET"] = str(installed)
            environment["HAXS_R32_OFFICIAL_NONCE"] = secrets.token_hex(32)
            completed = subprocess.run(
                [
                    sys.executable,
                    "-I",
                    "scripts/run_stage5c2gR32_phase_quadrature.py",
                    "--config",
                    "configs/stage5c2gR32/g1_phase_quadrature.yaml",
                    "--out",
                    str(output),
                ],
                cwd=ROOT,
                env=environment,
                text=True,
            )
            if completed.returncode != 0:
                raise RuntimeError("official deterministic G1 predicate failed")
        verification = json.loads(
            (output / "verification.json").read_text(encoding="utf-8")
        )
        if verification.get("status") != "PASS":
            raise RuntimeError("official deterministic G1 did not pass")
        terminal = {
            **{key: value for key, value in running.items() if key != "state_sha256"},
            "status": "PASSED",
            "verification_sha256": sha256_file(output / "verification.json"),
            "manifest_sha256": sha256_file(output / "MANIFEST.json"),
            "error": "",
        }
        terminal["state_sha256"] = sha256_payload(terminal)
        atomic_write_json(state_path, terminal)
        print(
            json.dumps(
                {
                    "gate": "G1",
                    "status": "PASSED",
                    "attempt_id": attempt_id,
                    "candidate_sha256": candidate["candidate_sha256"],
                    "state_sha256": terminal["state_sha256"],
                    "next": "STOP_AND_RETURN_FOR_SUPERVISORY_REVIEW",
                },
                indent=2,
                sort_keys=True,
            )
        )
    except Exception as error:
        failed = {
            **{key: value for key, value in running.items() if key != "state_sha256"},
            "status": "FAILED",
            "error": repr(error),
        }
        failed["state_sha256"] = sha256_payload(failed)
        atomic_write_json(state_path, failed)
        raise


if __name__ == "__main__":
    main()
