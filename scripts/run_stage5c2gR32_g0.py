#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from stage5c2gR32_common import atomic_write_json, sha256_file, sha256_payload


def _candidate() -> tuple[dict, Path]:
    choices = [
        ROOT / "CANDIDATE.stage5c2gR32.json",
        ROOT / "results/stage5c2gR32/protocol/CANDIDATE.json",
    ]
    existing = [path for path in choices if path.is_file()]
    if len(existing) != 1:
        raise RuntimeError("expected exactly one canonical R3.2 candidate record")
    payload = json.loads(existing[0].read_text(encoding="utf-8"))
    canonical = {key: value for key, value in payload.items() if key != "candidate_sha256"}
    if payload.get("candidate_sha256") != sha256_payload(canonical):
        raise RuntimeError("R3.2 candidate self-identity failed")
    return payload, existing[0]


def _verify_runtime(candidate: dict) -> None:
    observed = {}
    for relative, expected in candidate["runtime_files"].items():
        path = ROOT / relative
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"candidate runtime file missing or unsafe: {relative}")
        observed[relative] = sha256_file(path)
        if observed[relative] != expected:
            raise RuntimeError(f"candidate runtime file changed: {relative}")
    if sha256_payload(observed) != candidate["runtime_tree_sha256"]:
        raise RuntimeError("candidate runtime tree digest failed")
    for gate, record in candidate["pre_candidate_gates"].items():
        for path_key, digest_key in [
            ("path", "sha256"),
            ("manifest_path", "manifest_sha256"),
        ]:
            if path_key in record and sha256_file(ROOT / record[path_key]) != record[digest_key]:
                raise RuntimeError(f"candidate-bound {gate} evidence changed")
        for relative, digest in record.get("supplemental", {}).items():
            if sha256_file(ROOT / relative) != digest:
                raise RuntimeError(f"candidate-bound {gate} supplemental evidence changed")


def _hardware_identity() -> dict:
    values = []
    if platform.system() == "Darwin":
        completed = subprocess.run(
            ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
            text=True,
            capture_output=True,
        )
        values.append(completed.stdout)
    else:
        for path in [Path("/etc/machine-id"), Path("/var/lib/dbus/machine-id")]:
            if path.is_file():
                values.append(path.read_text(encoding="utf-8").strip())
                break
        values.extend([platform.node(), platform.machine()])
    raw = "|".join(values)
    return {
        "system": platform.system(),
        "machine": platform.machine(),
        "physical_host_sha256": hashlib.sha256(raw.encode()).hexdigest(),
    }


def _run(name: str, command: list[str], out: Path, environment: dict) -> dict:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    transcript = out / f"{name}.txt"
    transcript.write_text(completed.stdout, encoding="utf-8")
    return {
        "name": name,
        "command": command,
        "exit_status": completed.returncode,
        "transcript": transcript.name,
        "transcript_sha256": sha256_file(transcript),
    }


def run(host_tag: str, protocol_archive: Path, out: Path) -> dict:
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError("R3.2 G0 requires CPython 3.12")
    candidate, candidate_path = _candidate()
    _verify_runtime(candidate)
    if sha256_file(protocol_archive) == "":
        raise RuntimeError("unreachable protocol archive identity")
    out.mkdir(parents=True, exist_ok=False)
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
    environment.update(
        {
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "VECLIB_MAXIMUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
        }
    )
    checks = [
        _run(
            "00_compileall",
            [
                sys.executable,
                "-I",
                "-m",
                "compileall",
                "-q",
                "src",
                "scripts",
                "scripts_patch",
                "tests",
            ],
            out,
            environment,
        ),
        _run(
            "01_full_tests",
            [sys.executable, "scripts/run_tests.py"],
            out,
            environment,
        ),
        _run(
            "02_targeted_tests",
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/stage5c2gR32",
                "tests/stage5c2gR3",
                "tests/regression",
                "-q",
            ],
            out,
            environment,
        ),
    ]
    wheel = ROOT / candidate["wheel"]["path"]
    if not wheel.is_file():
        wheel = ROOT / Path(candidate["wheel"]["path"]).name
    if sha256_file(wheel) != candidate["wheel"]["sha256"]:
        raise RuntimeError("candidate-bound wheel is missing or changed")
    with tempfile.TemporaryDirectory(prefix="stage5c2gR32_g0_install_") as name:
        installed = Path(name) / "installed"
        installed.mkdir()
        checks.append(
            _run(
                "03_immutable_wheel_install",
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
                out,
                environment,
            )
        )
        probe = (
            "import json,pathlib,sys;"
            "sys.path.insert(0,sys.argv[1]);import haxs;"
            "p=pathlib.Path(haxs.__file__).resolve();"
            "print(json.dumps({'isolated':bool(sys.flags.isolated),'origin':str(p),"
            "'from_target':pathlib.Path(sys.argv[1]).resolve() in p.parents}))"
        )
        checks.append(
            _run(
                "04_isolated_import",
                [sys.executable, "-I", "-c", probe, str(installed)],
                out,
                environment,
            )
        )
    _verify_runtime(candidate)
    status = "PASS" if all(item["exit_status"] == 0 for item in checks) else "FAIL"
    attestation = {
        "schema_version": "haxs.stage5c2gR32.g0-host.v1",
        "host_tag": host_tag,
        "status": status,
        "candidate_sha256": candidate["candidate_sha256"],
        "runtime_tree_sha256": candidate["runtime_tree_sha256"],
        "wheel_sha256": candidate["wheel"]["sha256"],
        "protocol_archive_sha256": sha256_file(protocol_archive),
        "python_version": platform.python_version(),
        "python_executable_sha256": sha256_file(sys.executable),
        "platform": {
            "system": platform.system(),
            "machine": platform.machine(),
            "release": platform.release(),
        },
        "physical_host": _hardware_identity(),
        "checks": checks,
        "scientific_execution_performed": False,
    }
    attestation["attestation_sha256"] = sha256_payload(attestation)
    atomic_write_json(out / "HOST_ATTESTATION.json", attestation)
    return attestation


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host-tag", required=True)
    parser.add_argument("--protocol-archive", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    result = run(args.host_tag, args.protocol_archive, args.out)
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
