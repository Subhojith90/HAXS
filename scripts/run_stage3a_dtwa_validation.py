#!/usr/bin/env python
from __future__ import annotations
import argparse, json, math, sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from haxs.lattice.graphs import hypercubic_lattice
from haxs.methods.dtwa import sample_css_x, run_dtwa
from haxs.io.result_store import ensure_dir, save_dataframe, save_json


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--config', default='configs/stage3a_lite/validation_repair.yaml')
    ap.add_argument('--out', default='results/stage3a_lite/dtwa_validation')
    args=ap.parse_args()
    out=ensure_dir(ROOT/args.out)
    g=hypercubic_lattice((4,), False)
    times=np.linspace(0,0.4,9)
    res=run_dtwa(g,times,hole_fraction=0.0,n_traj=2048,seed=9101,store_trajectories=True)
    cols=list(res['columns']); data=np.asarray(res['data'])
    curve=pd.DataFrame(data, columns=cols)
    save_dataframe(out/'dtwa_validation_curve.csv', curve, {'stage':'stage3a','config':args.config})
    spins=sample_css_x(2048,4,seed=9101+43)
    phase_norm=float(np.mean(np.linalg.norm(spins,axis=-1)))
    phase_norm_std=float(np.std(np.linalg.norm(spins,axis=-1)))
    spin0=float(curve.loc[0,'spin_length']); spin1=float(curve.loc[1,'spin_length'])
    xi2db0=float(curve.loc[0,'xi2_db'])
    rows=[
        {'gate':'css_phase_point_norm','value':phase_norm,'target':math.sqrt(3)/2,'passed':abs(phase_norm-math.sqrt(3)/2)<1e-12},
        {'gate':'css_xi2_db_t0_near_zero','value':xi2db0,'target':0.0,'passed':abs(xi2db0)<0.45},
        {'gate':'spin_length_t0_near_one','value':spin0,'target':1.0,'passed':spin0>0.95},
        {'gate':'no_first_step_collapse','value':spin1,'target':'>0.90 and not 1/sqrt(3)','passed':(spin1>0.90 and abs(spin1-1/math.sqrt(3))>0.05)},
        {'gate':'short_time_spin_length_change_small','value':abs(spin1-spin0),'target':'<0.10','passed':abs(spin1-spin0)<0.10},
    ]
    summary=pd.DataFrame(rows)
    save_dataframe(out/'dtwa_validation_summary.csv', summary, {'stage':'stage3a','config':args.config})
    passed=bool(summary['passed'].all())
    save_json(out/'dtwa_validation_manifest.json', {'stage':'stage3a','passed':passed,'spin_length_t0':spin0,'spin_length_first_step':spin1,'xi2_db_t0':xi2db0,'phase_point_norm_mean':phase_norm,'phase_point_norm_std':phase_norm_std})
    print(f'stage3a DTWA validation wrote {out}; passed={passed}; spin_length_first_step={spin1:.6f}')
    if not passed:
        raise SystemExit(2)
if __name__=='__main__': main()
