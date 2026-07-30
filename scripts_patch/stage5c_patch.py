from pathlib import Path
import textwrap

ROOT = Path.cwd()

Path("configs/stage5c_lite").mkdir(parents=True, exist_ok=True)
Path("tests/stage5c").mkdir(parents=True, exist_ok=True)
Path("docs/stage5c").mkdir(parents=True, exist_ok=True)

Path("configs/stage5c_lite/controlled_release.yaml").write_text("""stage5c:
  mode: controlled_release_checkpoint
  source_stage: stage5b1
  repair_stage: stage5b1R
  broad_compute_allowed: false
  publication_claim_allowed: false
""")

Path("scripts/run_stage5c_controlled_release.py").write_text(r'''import argparse, json
from pathlib import Path
import pandas as pd

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    local = Path("results/stage5b1R_lite/repaired_existing/stage5b1R_curve_based_local_window.csv")
    contrast = Path("results/stage5b1R_lite/repaired_existing/stage5b1R_per_contrast_uncertainty.csv")

    summary = {
        "stage": "stage5c_controlled_release_checkpoint",
        "broad_compute_allowed": False,
        "publication_claim_allowed": False,
        "uses_stage5b1R_repaired_diagnostics": local.exists() and contrast.exists(),
        "route": "stage5c_controlled_checkpoint_no_broad_compute",
    }

    if local.exists():
        df = pd.read_csv(local)
        summary["local_window_all_negative"] = bool(df["negative"].all())

    if contrast.exists():
        cf = pd.read_csv(contrast)
        core = cf[cf["contrast"] == "core_static_minus_mobile_plus_sd"]
        summary["core_contrast_strict_negative_blocks"] = int(core["strict_negative"].sum()) if not core.empty else 0
        summary["total_strict_negative_contrasts"] = int(cf["strict_negative"].sum())

    pd.DataFrame([summary]).to_csv(out / "stage5c_controlled_summary.csv", index=False)
    (out / "stage5c_controlled_decision.json").write_text(json.dumps(summary, indent=2))
    print("stage5c controlled checkpoint wrote", out)

if __name__ == "__main__":
    main()
''')

Path("scripts/make_stage5c_controlled_report.py").write_text(r'''import argparse
from pathlib import Path
import pandas as pd

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    summary_path = Path(args.results) / "controlled_release" / "stage5c_controlled_summary.csv"
    summary = pd.read_csv(summary_path).iloc[0].to_dict() if summary_path.exists() else {}

    report = f"""# Stage 5C Controlled Release Checkpoint

## Verdict

This is a controlled Stage 5C design/release checkpoint, not a broad Stage 5C compute campaign.

## Route

`{summary.get("route", "stage5c_controlled_checkpoint_no_broad_compute")}`

## Current Status

- Broad compute allowed: `{summary.get("broad_compute_allowed", False)}`
- Publication claim allowed: `{summary.get("publication_claim_allowed", False)}`
- Uses Stage 5B1-R repaired diagnostics: `{summary.get("uses_stage5b1R_repaired_diagnostics", False)}`
- Local-window all negative: `{summary.get("local_window_all_negative", "NA")}`
- Core strict-negative blocks: `{summary.get("core_contrast_strict_negative_blocks", "NA")}`

## Interpretation

The project should not claim publication-grade finite-size evidence yet. This checkpoint consolidates Stage 5B1 and Stage 5B1-R repaired diagnostics and prepares the next supervisor review package.
"""
    target = out / "stage5c_controlled_report.md"
    target.write_text(report)
    print("stage5c report wrote", target)

if __name__ == "__main__":
    main()
''')

Path("scripts/run_stage5c_all_lite.py").write_text(r'''import subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def run(cmd):
    print("RUN:", " ".join(cmd))
    subprocess.run(cmd, cwd=ROOT, check=True)

def main():
    run([sys.executable, "scripts/run_stage5c_controlled_release.py", "--out", "results/stage5c_lite/controlled_release"])
    run([sys.executable, "scripts/make_stage5c_controlled_report.py", "--results", "results/stage5c_lite", "--out", "manuscript/stage5c_lite"])
    print("Stage 5C controlled lite complete.")

if __name__ == "__main__":
    main()
''')

Path("tests/stage5c/test_stage5c_controlled.py").write_text(r'''from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def test_stage5c_scripts_exist():
    assert (ROOT / "scripts/run_stage5c_controlled_release.py").exists()
    assert (ROOT / "scripts/make_stage5c_controlled_report.py").exists()
    assert (ROOT / "scripts/run_stage5c_all_lite.py").exists()

def test_stage5c_config_exists():
    assert (ROOT / "configs/stage5c_lite/controlled_release.yaml").exists()
''')

Path("docs/stage5c/STAGE5C_RUNBOOK.md").write_text("""# Stage 5C Controlled Runbook

This is a controlled checkpoint only.

Run:

```bash
pytest tests/stage5c tests/stage5b1R tests/regression -q
python scripts/run_stage5c_all_lite.py
```
                                                   """)