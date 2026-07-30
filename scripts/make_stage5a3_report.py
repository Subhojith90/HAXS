#!/usr/bin/env python
from pathlib import Path
import argparse, json
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
def load(p): return pd.read_csv(p) if Path(p).exists() else pd.DataFrame()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--results',default='results/stage5a3_lite'); ap.add_argument('--figures',default='figures/stage5a3_lite'); ap.add_argument('--out',default='manuscript/stage5a3_lite'); args=ap.parse_args()
    res=ROOT/args.results; base=res/'final_replication_lock'; out=ROOT/args.out; out.mkdir(parents=True,exist_ok=True)
    decision=json.loads((res/'decision/stage5a3_decision.json').read_text()) if (res/'decision/stage5a3_decision.json').exists() else {}
    summ=load(base/'stage5a3_replication_lock_summary.csv'); gates=load(base/'stage5a3_readiness_gates.csv')
    lines=['# Stage 5A3 Final Replication Lock Report','',f"**Route:** `{decision.get('route','unknown')}`",f"**Passed:** `{decision.get('passed',False)}`",'',
           '## Scope','Stage 5A3 locks the surviving `3x3x2` target-shape mechanism gate at a single high trajectory setting. It tests primary and independent replication seed blocks before any Stage 5B mechanism decomposition. It does not make publication claims.','',
           '## Replication-lock summary']
    if len(summ): lines.append(summ.to_markdown(index=False))
    lines += ['','## Readiness gates']
    if len(gates): lines.append(gates.to_markdown(index=False))
    lines += ['','## Interpretation','Proceed to Stage 5B only if both primary and independent replication blocks pass the fixed-time, interval, negative-seed, trajectory-fraction, and nested-stability gates.']
    (out/'stage5a3_report.md').write_text('\n'.join(lines)+'\n')
    print(f'stage5a3 report wrote {out}/stage5a3_report.md')
if __name__=='__main__': main()
