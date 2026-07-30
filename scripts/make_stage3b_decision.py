#!/usr/bin/env python
from __future__ import annotations
import argparse, sys
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from haxs.io.result_store import ensure_dir, save_dataframe, save_json

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--results',default='results/stage3b_lite'); ap.add_argument('--out',default='results/stage3b_lite/decision'); args=ap.parse_args()
    r=ROOT/args.results; out=ensure_dir(ROOT/args.out)
    val_path=r/'dtwa_validation/dtwa_validation_summary.csv'
    fs_path=r/'paired_finite_size/stage3b_paired_shape_effects.csv'
    dim_path=r/'paired_finite_size/stage3b_dimension_summary.csv'
    dtwa_pass=False
    if val_path.exists():
        val=pd.read_csv(val_path); dtwa_pass=bool(val['passed'].astype(bool).all())
    paired_pass=False; core_shapes=0; neg_shapes=0; dims_pass=0; mean_effect=None
    if fs_path.exists():
        df=pd.read_csv(fs_path)
        core=df[(df.pre_registered_core.astype(bool))&(df.metric=='xi2_db_min')]
        if len(core):
            core_shapes=int(((core.paired_mean_difference_a_minus_b<0)&(core.ci_excludes_zero.astype(bool))).sum())
            neg_shapes=int((core.paired_mean_difference_a_minus_b<0).sum())
            mean_effect=float(core.paired_mean_difference_a_minus_b.mean())
        if dim_path.exists():
            dim=pd.read_csv(dim_path)
            dims_pass=int(dim['all_shapes_negative'].astype(bool).sum()) if len(dim) else 0
        paired_pass=bool(core_shapes>=3 and dims_pass>=2)
    route='stage3b_ready_for_supervisor_or_stage3c' if (dtwa_pass and paired_pass) else ('stage3b_dtwa_passed_mechanism_not_stable' if dtwa_pass else 'stage3b_dtwa_gate_failed')
    table=pd.DataFrame([
        {'gate':'dtwa_validation_still_passes','passed':dtwa_pass},
        {'gate':'paired_core_effect_ci_excludes_zero_at_minimum_time_at_3plus_shapes','passed':core_shapes>=3,'value':core_shapes},
        {'gate':'core_effect_negative_in_2plus_dimension_families','passed':dims_pass>=2,'value':dims_pass},
        {'gate':'constructive_claim_remains_closed','passed':True},
    ])
    save_dataframe(out/'stage3b_decision_table.csv',table,{'stage':'stage3b'})
    save_json(out/'stage3b_decision.json',{'route':route,'dtwa_validation_passed':dtwa_pass,'paired_finite_size_passed':paired_pass,'core_shapes_passing':core_shapes,'core_shapes_negative':neg_shapes,'dimension_families_negative':dims_pass,'mean_core_shape_effect_db':mean_effect,'constructive_route':'closed_not_tested_as_success_claim'})
    print(f'stage3b decision wrote {out}; route={route}; core_shapes={core_shapes}; dims={dims_pass}')
if __name__=='__main__': main()
