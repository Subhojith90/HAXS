import argparse, json
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
