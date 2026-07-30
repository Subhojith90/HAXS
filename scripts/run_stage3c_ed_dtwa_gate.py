#!/usr/bin/env python
from __future__ import annotations
import argparse, sys, math, json
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'scripts'))
from stage2_common import load_raw_config
from haxs.io.result_store import ensure_dir, save_dataframe, save_json
from haxs.lattice.graphs import hypercubic_lattice
from haxs.methods.ed import run_ed_curve
from haxs.methods.dtwa import run_dtwa

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--config',default='configs/stage3c_preflight/preflight.yaml')
    ap.add_argument('--out',default='results/stage3c_preflight/ed_dtwa_gate')
    args=ap.parse_args()
    raw=load_raw_config(args.config); out=ensure_dir(ROOT/args.out)
    val=raw.get('validation',{}); model=raw.get('model',{})
    shape=tuple(val.get('ed_dtwa_shape',[4])); times=np.linspace(0,float(val.get('ed_dtwa_t_max',0.4)),int(val.get('ed_dtwa_n_steps',9)))
    g=hypercubic_lattice(shape,False)
    ed=run_ed_curve(g,times,j_perp=float(model.get('j_perp',1.0)),jz=float(model.get('jz',0.35)))
    dt=run_dtwa(g,times,j_perp=float(model.get('j_perp',1.0)),jz=float(model.get('jz',0.35)),hole_fraction=0.0,n_traj=int(val.get('ed_dtwa_n_traj',4096)),seed=int(raw.get('seed',1729))+911)
    ed_df=pd.DataFrame(ed['data'],columns=ed['columns']); dt_df=pd.DataFrame(dt['data'],columns=dt['columns'])
    merged=pd.DataFrame({'time':times,'ed_xi2':ed_df['xi2'],'dtwa_xi2':dt_df['xi2'],'ed_xi2_db':ed_df['xi2_db'],'dtwa_xi2_db':dt_df['xi2_db'],'ed_spin_length':ed_df['spin_length'],'dtwa_spin_length':dt_df['spin_length']})
    merged['xi2_error']=merged['dtwa_xi2']-merged['ed_xi2']; merged['xi2_db_error']=merged['dtwa_xi2_db']-merged['ed_xi2_db']; merged['spin_length_error']=merged['dtwa_spin_length']-merged['ed_spin_length']
    xi2_rmse=float(np.sqrt(np.mean(merged['xi2_error']**2)))
    xi2db_rmse=float(np.sqrt(np.mean(merged['xi2_db_error']**2)))
    spin_rmse=float(np.sqrt(np.mean(merged['spin_length_error']**2)))
    first=float(dt_df.loc[1,'spin_length']) if len(dt_df)>1 else float(dt_df.loc[0,'spin_length'])
    gates=[
      {'gate':'ed_dtwa_xi2_rmse','value':xi2_rmse,'threshold':float(val.get('xi2_rmse_threshold',0.02)),'passed':xi2_rmse<float(val.get('xi2_rmse_threshold',0.02))},
      {'gate':'ed_dtwa_xi2_db_rmse','value':xi2db_rmse,'threshold':float(val.get('xi2_db_rmse_threshold',0.10)),'passed':xi2db_rmse<float(val.get('xi2_db_rmse_threshold',0.10))},
      {'gate':'ed_dtwa_spin_length_rmse','value':spin_rmse,'threshold':float(val.get('spin_length_rmse_threshold',0.003)),'passed':spin_rmse<float(val.get('spin_length_rmse_threshold',0.003))},
      {'gate':'dtwa_first_step_spin_length','value':first,'threshold':float(val.get('first_step_spin_length_min',0.99)),'passed':first>float(val.get('first_step_spin_length_min',0.99))},
    ]
    gate_df=pd.DataFrame(gates)
    save_dataframe(out/'ed_dtwa_curve.csv',merged,raw)
    save_dataframe(out/'ed_dtwa_gates.csv',gate_df,raw)
    passed=bool(gate_df['passed'].all())
    save_json(out/'ed_dtwa_manifest.json',{'stage':'stage3c_preflight','passed':passed,'shape':shape,'n_traj':int(val.get('ed_dtwa_n_traj',4096)),'xi2_rmse':xi2_rmse,'xi2_db_rmse':xi2db_rmse,'spin_length_rmse':spin_rmse,'dtwa_first_step_spin_length':first})
    print(f'stage3c ED-DTWA gate wrote {out}; passed={passed}; xi2_db_rmse={xi2db_rmse:.6f}; spin_rmse={spin_rmse:.6g}')
    if not passed: raise SystemExit(2)
if __name__=='__main__': main()
