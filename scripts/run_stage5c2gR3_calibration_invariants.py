#!/usr/bin/env python
from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if not sys.flags.isolated:
    raise SystemExit("official G1 must be invoked through the isolated installed-wheel launcher")
launch_path = Path(os.environ.get("HAXS_G1_LAUNCH_ATTESTATION", ""))
if not launch_path.is_file() or launch_path.is_symlink():
    raise SystemExit("official G1 launch attestation is missing")
launch = json.loads(launch_path.read_text(encoding="utf-8"))
if set(launch) != {"schema_version", "candidate_sha256", "wheel_sha256", "installed_target", "execution_root", "nonce", "launcher_sha256"} or launch.get("schema_version") != "stage5c2gR3.1.G1-launch.v1" or Path(launch["execution_root"]).resolve() != ROOT.resolve():
    raise SystemExit("official G1 launch attestation schema or execution root failed")
installed_target = Path(launch["installed_target"]).resolve()
sys.path.insert(0, str(installed_target)); sys.path.insert(1, str(ROOT / "scripts"))
import haxs
if installed_target not in Path(haxs.__file__).resolve().parents:
    raise SystemExit("official G1 HAXS import did not originate from the candidate-bound installed wheel")
from haxs.lattice.graphs import hypercubic_lattice
from haxs.lattice.occupancy import sample_fixed_count
from haxs.methods.constrained_spin_hole import run_constrained_curve
from haxs.methods.dtwa import run_dtwa
from stage5c2gR3_common import assert_protocol_locked, canonical_config, physical_unit, plan_g1, production_label_parameters, require_isolated_interpreter, sha256_file
from stage5c2gR3_semantics import derive_g1_decision
from stage5c2gR3_semantics_reference import assert_semantic_agreement, derive_g1_decision_reference
from stage5c2gR3_state import assert_canonical_artifact_root, atomic_write_json, begin_attempt, build_raw_manifest, canonical_artifact_root, complete_attempt, fail_attempt


def initial_holes(case: dict, occupancy_idx: int, seed: int, n_sites: int) -> list[int]:
    if occupancy_idx == 0:
        return [int(value) for value in case["holes"]]
    occupancy = sample_fixed_count(n_sites, len(case["holes"]), seed)
    return np.flatnonzero(~occupancy).astype(int).tolist()


def main() -> None:
    require_isolated_interpreter(ROOT)
    if len(sys.argv) != 1:
        raise SystemExit("R3 G1 accepts no command-line configuration, evidence, or output overrides")
    lock = assert_protocol_locked()
    if launch["candidate_sha256"] != lock["candidate_sha256"] or launch["wheel_sha256"] != lock["candidate_payload"]["installed_wheel"]["wheel_sha256"]:
        raise RuntimeError("official G1 launch attestation differs from the protocol lock")
    raw, config_sha, plan_sha = canonical_config("G1", lock)
    stage = raw["stage5c2gR3_G1"]
    plan = plan_g1(raw)
    attempt_id = uuid.uuid4().hex
    running = begin_attempt("G1", lock, config_sha, plan_sha, attempt_id)
    attempt_root = canonical_artifact_root("G1", lock, config_sha, attempt_id)
    attempt_root.mkdir(parents=True, exist_ok=False)
    assert_canonical_artifact_root(attempt_root, ROOT)
    try:
        times = np.linspace(float(stage["times"]["start"]), float(stage["times"]["stop"]), int(stage["times"]["points"]))
        cases = {case["id"]: case for case in stage["cases"]}
        grouped: dict[tuple, list[dict]] = {}
        for row in plan:
            key = (row["case_id"], row["occupancy_idx"], row["path_idx"], row["phase_idx"])
            grouped.setdefault(key, []).append(row)
        curves, comparisons, registry, attempts = [], [], [], []
        for (case_id, occupancy_idx, path_idx, phase_idx), planned_rows in grouped.items():
            case = cases[case_id]
            graph = hypercubic_lattice(tuple(case["shape"]), False)
            unit = physical_unit(stage["namespace_uuid"], "G1", case_id, occupancy_idx, path_idx, phase_idx)
            holes = initial_holes(case, occupancy_idx, unit["occupancy_seed"], graph.n_sites)
            occupancy = np.ones(graph.n_sites, dtype=bool); occupancy[holes] = False
            results: dict[tuple[str, str], dict] = {}
            for label in case["labels"]:
                hopping, exact_lambda, eta, surrogate_lambda = production_label_parameters(label, stage["model"], case.get("overrides"))
                results[("exact", label)] = run_constrained_curve(graph, times, holes, j_perp=float(stage["model"]["j_perp"]), jz=float(stage["model"]["jz"]), hopping_t=hopping, lambda_sd=exact_lambda)
                results[("surrogate", label)] = run_dtwa(graph, times, j_perp=float(stage["model"]["j_perp"]), jz=float(stage["model"]["jz"]), mobile_eta=eta, lambda_sd=surrogate_lambda, n_traj=int(stage["n_traj_per_phase_batch"]), initial_occupancy=occupancy, fixed_hole_count=len(holes), occupancy_seed=unit["occupancy_seed"], hole_path_seed=unit["hole_path_seed"], phase_batch_seed=unit["phase_batch_seed"])
            for planned in planned_rows:
                method = str(planned["method"])
                labels = [str(planned["static_label"]), str(planned["comparison_label"])]
                for label in labels:
                    result = results[(method, label)]
                    frame = pd.DataFrame(result["data"], columns=result["columns"])
                    frame.insert(0, "method", method); frame.insert(0, "label", label); frame.insert(0, "comparison_id", planned["comparison_id"])
                    frame.insert(0, "schema_version", stage["schema_version"])
                    curves.append(frame)
                left = np.asarray(results[(method, labels[0])]["data"], dtype=float)
                right = np.asarray(results[(method, labels[1])]["data"], dtype=float)
                comparisons.append({"comparison_id": planned["comparison_id"], "reported_max_abs_full_curve_difference_non_authoritative": float(np.max(np.abs(left - right)))})
                registry.append(planned)
                attempts.append({"comparison_id": planned["comparison_id"], "status": "completed", "attempt_id": attempt_id})
        files = {
            "curves": attempt_root / "g1_curves.csv",
            "comparisons": attempt_root / "g1_comparisons_non_authoritative.csv",
            "registry": attempt_root / "g1_registry.csv",
            "attempts": attempt_root / "g1_attempts.csv",
            "semantic_decision": attempt_root / "g1_semantic_decision.json",
            "runtime_attestation": attempt_root / "g1_runtime_import_attestation.json",
        }
        pd.concat(curves, ignore_index=True).to_csv(files["curves"], index=False)
        pd.DataFrame(comparisons).to_csv(files["comparisons"], index=False)
        pd.DataFrame(registry).to_csv(files["registry"], index=False)
        pd.DataFrame(attempts).to_csv(files["attempts"], index=False)
        primary = derive_g1_decision(files["curves"], files["registry"], raw)
        reference = derive_g1_decision_reference(files["curves"], files["registry"], raw)
        assert_semantic_agreement(primary, reference)
        atomic_write_json(files["semantic_decision"], primary)
        module_origins = {name: str(Path(module.__file__).resolve()) for name, module in {"haxs": haxs, "numpy": np, "pandas": pd}.items()}
        native_libraries = sorted({(Path(module.__file__).name, sha256_file(module.__file__)) for module in list(sys.modules.values()) if getattr(module, "__file__", None) and Path(module.__file__).suffix in {".so", ".dylib", ".pyd"}})
        runtime_attestation = {"schema_version": "stage5c2gR3.1.G1-runtime.v1", "candidate_sha256": lock["candidate_sha256"], "wheel_sha256": launch["wheel_sha256"], "isolated": bool(sys.flags.isolated), "installed_target": str(installed_target), "haxs_from_installed_wheel": installed_target in Path(haxs.__file__).resolve().parents, "sys_path": sys.path, "module_origins": module_origins, "native_libraries": [{"name": name, "sha256": digest} for name, digest in native_libraries]}
        atomic_write_json(files["runtime_attestation"], runtime_attestation)
        expected_ids = [row["comparison_id"] for row in plan]
        manifest = build_raw_manifest("G1", attempt_root, files, expected_ids, expected_ids, lock, config_sha, plan_sha, attempt_id)
        manifest_path = attempt_root / "MANIFEST.json"
        atomic_write_json(manifest_path, manifest)
        manifest_relative = manifest_path.relative_to(ROOT).as_posix()
        state = complete_attempt("G1", lock, attempt_id, int(running["sequence"]), manifest_relative)
        print(json.dumps({"gate": "G1", "status": "PASSED", "attempt_id": attempt_id, "state_sha256": state["state_sha256"], "manifest_sha256": manifest["manifest_sha256"], "semantic_decision_sha256": primary["decision_sha256"], "rows": len(primary["rows"]), "maximum_difference": primary["maximum_difference"], "next": "STOP_AND_RETURN_FOR_SUPERVISORY_REVIEW"}, indent=2))
    except Exception as error:
        try:
            fail_attempt("G1", lock, attempt_id, int(running["sequence"]), repr(error))
        except RuntimeError:
            pass
        raise


if __name__ == "__main__":
    main()
