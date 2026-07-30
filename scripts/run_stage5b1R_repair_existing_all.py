import subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def run(cmd): print('RUN:',' '.join(map(str,cmd))); subprocess.run(cmd,cwd=ROOT,check=True)
def main():
 inp='results/stage5b1_lite/replicated_five_label'; out='results/stage5b1R_lite/repaired_existing_v2'
 run([sys.executable,'scripts/run_stage4_validation_stack.py','--out','results/stage5b1R_lite/validation'])
 run([sys.executable,'scripts/run_stage5b1R_repair_existing_curves.py','--input',inp,'--out',out])
 run([sys.executable,'scripts/run_stage5b1R_per_contrast_uncertainty.py','--input',inp,'--out',out])
 print('Stage 5B1-R v2 repair-existing diagnostics complete.')
if __name__=='__main__':main()
