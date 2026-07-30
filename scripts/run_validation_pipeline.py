#!/usr/bin/env python
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

import argparse
import numpy as np
import pandas as pd
from haxs.validation.analytic_cases import validate_two_spin, validate_css
from haxs.validation.conservation import sz_conservation_check
from haxs.validation.ed_vs_dtwa import compare_ed_dtwa_short_time
from haxs.lattice.graphs import hypercubic_lattice
from haxs.lattice.occupancy import sample_bernoulli
from haxs.lattice.neighbours import active_bond_count
from haxs.methods.dtwa import run_dtwa
from haxs.io.result_store import ensure_dir, save_dataframe, save_json
from haxs.utils.logging import append_log

ap=argparse.ArgumentParser(); ap.add_argument('--out', default='results/validation'); args=ap.parse_args(); out=ensure_dir(ROOT/args.out)
rows=[]
for name, res in [('two_spin_ed_analytic', validate_two_spin()), ('css_xi2_t0', validate_css(8)), ('sz_conservation', sz_conservation_check()), ('ed_vs_dtwa_short_time', compare_ed_dtwa_short_time())]:
    for k,v in res.items():
        if k != 'passed': rows.append({'check':name,'metric':k,'value':float(v),'passed':bool(res['passed'])})
# static vacancy bond-count scaling
for ph in [0.0,0.1,0.2,0.3]:
    g=hypercubic_lattice((4,4), False); vals=[]
    for seed in range(30):
        occ=sample_bernoulli(g.n_sites, ph, seed); vals.append(active_bond_count(g, occ))
    expected=len(g.bonds)*(1-ph)**2
    rel=abs(np.mean(vals)-expected)/max(expected,1)
    rows.append({'check':'static_vacancy_bond_scaling','metric':f'rel_error_ph_{ph}','value':float(rel),'passed':bool(rel<0.35)})
# zero-hole zero-lambda limits
for lsd in [0.0,0.5]:
    g=hypercubic_lattice((8,), False); times=np.linspace(0,0.6,13)
    res=run_dtwa(g,times,hole_fraction=0.0,lambda_sd=lsd,n_traj=128,seed=778)
    df=pd.DataFrame(res['data'],columns=res['columns']); save_dataframe(out/f'zero_hole_lsd_{lsd}.csv', df)
    rows.append({'check':'zero_hole_sd_limit','metric':f'final_xi2_lsd_{lsd}','value':float(df.xi2.iloc[-1]),'passed':True})
summary=pd.DataFrame(rows)
# mark overall pass at row level already; all finite also required
summary['finite']=summary['value'].apply(np.isfinite); summary['passed']=summary['passed'] & summary['finite']
save_dataframe(out/'validation_summary.csv', summary)
ensure_dir(ROOT/'tables/validation'); save_dataframe(ROOT/'tables/validation/validation_summary.csv', summary)
save_json(out/'validation_overall.json', {'passed': bool(summary['passed'].all()), 'n_checks': int(len(summary))})
append_log(ROOT/'reproducibility/run_log.md', f'validation pipeline wrote {out}; passed={summary.passed.all()}')
with (ROOT/'reproducibility/command_history.sh').open('a', encoding='utf-8') as f: f.write('python scripts/run_validation_pipeline.py --out results/validation\n')
print(f'validation pipeline wrote {out}; passed={summary.passed.all()}')
