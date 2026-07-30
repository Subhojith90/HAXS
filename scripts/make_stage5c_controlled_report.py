import argparse
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
