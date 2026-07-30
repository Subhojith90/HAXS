#!/usr/bin/env python
from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str]) -> None:
    started = datetime.now(timezone.utc).isoformat()
    print(f"START {started}: {' '.join(command)}", flush=True)
    completed = subprocess.run(command, cwd=ROOT)
    ended = datetime.now(timezone.utc).isoformat()
    print(f"END {ended}: exit={completed.returncode}", flush=True)
    completed.check_returncode()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/stage5c2f/primary_lock.yaml")
    ap.add_argument("--out", default="results/stage5c2f")
    ap.add_argument("--preflight", action="store_true")
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()
    py = sys.executable
    # The artifact gate must be offline-reproducible; use the environment's
    # already-installed build backend instead of contacting a package index.
    install_prefix = str(ROOT / args.out / "preflight" / "install_prefix")
    run([py, "-m", "pip", "install", "-e", ".", "--no-deps", "--no-build-isolation", "--ignore-installed", "--prefix", install_prefix])
    run([py, "scripts/run_tests.py"])
    run([py, "scripts/run_stage4_validation_stack.py", "--out", f"{args.out}/validation"])
    run([py, "scripts/check_stage5c2f_hierarchy.py", "--config", args.config, "--out", f"{args.out}/preflight", "--fail-on-collision", "--fail-on-multiple-occupancy-hash"])
    if args.preflight:
        run([py, "scripts/run_stage5c2f_primary_lock.py", "--config", args.config, "--out", f"{args.out}/primary", "--dry-run"])
    else:
        production = [py, "scripts/run_stage5c2f_primary_lock.py", "--config", args.config, "--out", f"{args.out}/primary"]
        if args.resume:
            production.append("--resume")
        run(production)
        run([py, "scripts/check_stage5c2f_hierarchy.py", "--config", args.config, "--registry", f"{args.out}/primary/stage5c2f_seed_registry.csv", "--out", f"{args.out}/preflight", "--fail-on-collision", "--fail-on-multiple-occupancy-hash"])
        run([py, "scripts/analyze_stage5c2f.py", "--config", args.config, "--primary", f"{args.out}/primary", "--out", f"{args.out}/analysis"])
        run([py, "scripts/make_stage5c2f_decision.py", "--analysis", f"{args.out}/analysis", "--hierarchy-gate", f"{args.out}/preflight/stage5c2f_hierarchy_gate.json"])
        run([py, "scripts/make_stage5c2f_report.py", "--analysis", f"{args.out}/analysis"])
    run([py, "scripts/make_stage5c2f_manifest.py", "--root", ".", "--out", "MANIFEST.sha256"])
    run([py, "scripts/verify_manifest.py", "--root", ".", "--manifest", "MANIFEST.sha256"])


if __name__ == "__main__":
    main()
