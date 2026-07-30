#!/usr/bin/env python
from pathlib import Path
import argparse, json
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
def load(p): return pd.read_csv(p) if Path(p).exists() else pd.DataFrame()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--results',default='results/stage5aR_lite'); ap.add_argument('--figures',default='figures/stage5aR_lite'); ap.add_argument('--out',default='manuscript/stage5aR_lite'); args=ap.parse_args()
    res=ROOT/args.results; base=res/'convergence_replication'; out=ROOT/args.out; out.mkdir(parents=True,exist_ok=True)
    decision=json.loads((res/'decision/stage5aR_decision.json').read_text()) if (res/'decision/stage5aR_decision.json').exists() else {}
    summ=load(base/'stage5a_convergence_replication_summary.csv'); conv=load(base/'stage5a_ntraj_convergence.csv'); gates=load(base/'stage5a_readiness_gates.csv')
    lines=['# Stage 5A-R Convergence and Replication Gate Report','',f"**Route:** `{decision.get('route','unknown')}`",f"**Passed:** `{decision.get('passed',False)}`",'','## Scope','Stage 5A-R tests whether the single surviving `3x3x2` mechanism signal is trajectory-converged and independently seed-replicated. It does not make publication claims.','','## Summary']
    if len(summ): lines.append(summ.to_markdown(index=False))
    lines += ['','## Convergence']
    if len(conv): lines.append(conv.to_markdown(index=False))
    lines += ['','## Readiness Gates']
    if len(gates): lines.append(gates.to_markdown(index=False))
    lines += ['','## Interpretation','Proceed to Stage 5B only if the convergence and independent replication gates pass. Otherwise, increase trajectory count or treat the mechanism evidence as directional/diagnostic.']
    (out/'stage5aR_report.md').write_text('\n'.join(lines)+'\n')
    print(f'stage5a report wrote {out}/stage5aR_report.md')
if __name__=='__main__': main()
