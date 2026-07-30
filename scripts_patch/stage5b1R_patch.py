from pathlib import Path

ROOT = Path.cwd()

# 1. New real curve-based local-window repair script
Path("scripts/run_stage5b1R_repair_existing_curves.py").write_text(r'''
import argparse
from pathlib import Path
import pandas as pd

def mean_at_time(df, label, t):
    sub = df[df["label"] == label].copy()
    sub["dt"] = (sub["t"] - t).abs()
    nearest_t = sub.sort_values("dt")["t"].iloc[0]
    return sub[sub["t"] == nearest_t]["xi2_db"].mean(), nearest_t

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    inp = Path(args.input)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    rows = []
    for block in ["primary_campaign", "replication_campaign"]:
        curves = pd.read_csv(inp / block / "stage4_curves_all.csv")
        finals = pd.read_csv(inp / block / "stage4_primary_pair_effects.csv")
        fixed_t = float(finals["fixed_time"].iloc[0]) if "fixed_time" in finals.columns else float(curves["t"].median())

        for offset in [-0.10, 0.0, 0.10]:
            target_t = fixed_t + offset
            static_mean, actual_t = mean_at_time(curves, "static_only", target_t)
            mobile_sd_mean, _ = mean_at_time(curves, "mobile_plus_spin_density", target_t)
            effect = static_mean - mobile_sd_mean

            rows.append({
                "block": block.replace("_campaign", ""),
                "offset": offset,
                "target_t": target_t,
                "actual_t": actual_t,
                "static_only_mean_xi2_db": static_mean,
                "mobile_plus_spin_density_mean_xi2_db": mobile_sd_mean,
                "core_effect_db": effect,
                "negative": effect < 0,
            })

    pd.DataFrame(rows).to_csv(out / "stage5b1R_curve_based_local_window.csv", index=False)
    print("wrote", out / "stage5b1R_curve_based_local_window.csv")

if __name__ == "__main__":
    main()
''')

# 2. New per-contrast uncertainty repair script
Path("scripts/run_stage5b1R_per_contrast_uncertainty.py").write_text(r'''
import argparse
from pathlib import Path
import pandas as pd
import numpy as np

CONTRASTS = [
    ("static_only", "mobile_plus_spin_density", "core_static_minus_mobile_plus_sd"),
    ("static_only", "mobile_only", "component_static_minus_mobile_only"),
    ("static_only", "spin_density_only", "component_static_minus_spin_density_only"),
    ("mobile_only", "mobile_plus_spin_density", "mobile_only_minus_mobile_plus_sd"),
    ("spin_density_only", "mobile_plus_spin_density", "spin_density_only_minus_mobile_plus_sd"),
]

def summarize_block(campaign_dir, block):
    finals = pd.read_csv(Path(campaign_dir) / "stage4_finals.csv")
    rows = []

    for a, b, name in CONTRASTS:
        aa = finals[finals["label"] == a]
        bb = finals[finals["label"] == b]

        if aa.empty or bb.empty:
            continue

        key_cols = [c for c in ["shape", "seed", "disorder_seed", "trajectory_rep"] if c in finals.columns]
        if key_cols:
            merged = aa.merge(bb, on=key_cols, suffixes=("_a", "_b"))
            va = "xi2_db_fixed_a" if "xi2_db_fixed_a" in merged.columns else "fixed_xi2_db_a"
            vb = "xi2_db_fixed_b" if "xi2_db_fixed_b" in merged.columns else "fixed_xi2_db_b"
            if va not in merged.columns:
                numeric_a = [c for c in merged.columns if c.endswith("_a") and "xi2" in c and "db" in c.lower()]
                numeric_b = [c for c in merged.columns if c.endswith("_b") and "xi2" in c and "db" in c.lower()]
                va, vb = numeric_a[0], numeric_b[0]
            diff = merged[va] - merged[vb]
        else:
            diff = pd.Series([aa.select_dtypes("number").iloc[:, -1].mean() - bb.select_dtypes("number").iloc[:, -1].mean()])

        mean = float(diff.mean())
        sd = float(diff.std(ddof=1)) if len(diff) > 1 else 0.0
        se = sd / np.sqrt(max(len(diff), 1))
        ci_low = mean - 1.96 * se
        ci_high = mean + 1.96 * se
        neg_frac = float((diff < 0).mean())

        rows.append({
            "block": block,
            "contrast": name,
            "n": int(len(diff)),
            "mean_db": mean,
            "ci_low_approx": ci_low,
            "ci_high_approx": ci_high,
            "negative_fraction": neg_frac,
            "strict_negative": bool(mean < 0 and ci_high < 0 and neg_frac >= 0.70),
        })
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    inp = Path(args.input)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    rows = []
    rows += summarize_block(inp / "primary_campaign", "primary")
    rows += summarize_block(inp / "replication_campaign", "replication")

    df = pd.DataFrame(rows)
    df.to_csv(out / "stage5b1R_per_contrast_uncertainty.csv", index=False)
    print("wrote", out / "stage5b1R_per_contrast_uncertainty.csv")

if __name__ == "__main__":
    main()
''')

# 3. Stage 5B1-R all-lite wrapper using existing curves first
Path("scripts/run_stage5b1R_repair_existing_all.py").write_text(r'''
import subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def run(cmd):
    print("RUN:", " ".join(cmd))
    subprocess.run(cmd, cwd=ROOT, check=True)

def main():
    inp = "results/stage5b1_lite/replicated_five_label"
    out = "results/stage5b1R_lite/repaired_existing"

    run([sys.executable, "scripts/run_stage4_validation_stack.py", "--out", "results/stage5b1R_lite/validation"])
    run([sys.executable, "scripts/run_stage5b1R_repair_existing_curves.py", "--input", inp, "--out", out])
    run([sys.executable, "scripts/run_stage5b1R_per_contrast_uncertainty.py", "--input", inp, "--out", out])

    print("Stage 5B1-R repair-existing diagnostics complete.")

if __name__ == "__main__":
    main()
''')

# 4. Numerical regression tests
Path("tests/stage5b1R").mkdir(parents=True, exist_ok=True)
Path("tests/stage5b1R/test_stage5b1R_repair_scripts.py").write_text(r'''
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def test_curve_repair_script_exists():
    assert (ROOT / "scripts/run_stage5b1R_repair_existing_curves.py").exists()

def test_per_contrast_uncertainty_script_exists():
    assert (ROOT / "scripts/run_stage5b1R_per_contrast_uncertainty.py").exists()

def test_repair_wrapper_exists():
    assert (ROOT / "scripts/run_stage5b1R_repair_existing_all.py").exists()
''')

print("Stage 5B1-R patch files written.")
