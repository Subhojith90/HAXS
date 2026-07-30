import subprocess, sys
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
