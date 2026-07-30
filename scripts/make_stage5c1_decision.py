#!/usr/bin/env python
from __future__ import annotations
import argparse, json
from pathlib import Path
import pandas as pd, yaml
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(); p.add_argument('--config',default='configs/stage5c1_c2_lite/conditional_pipeline.yaml'); p.add_argument('--results',default='results/stage5c1_c2_lite'); a=p.parse_args()
 st=yaml.safe_load((ROOT/a.config).read_text())['stage5c1_c2']; base=ROOT/a.results/'stage5c1_replication_resolution'; d=base/'diagnostics'
 nested=pd.read_csv(d/'stage5b1R_per_contrast_nested_uncertainty.csv'); local=pd.read_csv(d/'stage5b1R_curve_based_local_window.csv')
 core=nested[nested.contrast=='core_static_minus_mobile_plus_sd'].set_index('block')
 rep=nested[nested.block=='replication']; primary=nested[nested.block=='primary']
 reasons=[]
 if set(core.index)!={'primary','replication'}: reasons.append('missing_primary_or_replication_core')
 else:
  if not bool(core.loc['replication','strict_negative']): reasons.append('replication_core_gate_not_passed')
  delta=abs(float(core.loc['primary','mean_effect_db'])-float(core.loc['replication','mean_effect_db']))
  if delta>float(st['block_compatibility_abs_db_below']): reasons.append('primary_replication_core_incompatible')
 if not bool(local['negative'].all()): reasons.append('curve_based_local_window_not_negative')
 # Component gate required only for the independently rerun replication block; old primary remains locked reference.
 rep_components=rep[rep.contrast.str.startswith('component_')]
 if len(rep_components)!=2 or not bool(rep_components.strict_negative.all()): reasons.append('replication_component_gates_not_all_passed')
 allowed=not reasons
 out=base/'decision'; out.mkdir(parents=True,exist_ok=True)
 payload={'stage':'stage5c1_replication_resolution_decision','stage5c2_holdout_preflight_allowed':allowed,'broad_finite_size_stage5c_allowed':False,'route':'stage5c2_holdout_geometry_preflight' if allowed else 'stage5c1_more_replication_resolution_needed','reasons':reasons or ['Stage 5C.1 passes; launch Stage 5C.2 holdout geometry preflight only.'],'claim_scope':'C.1 locks target-shape estimator control; C.2 remains a conditional holdout preflight, not broad finite-size compute.'}
 (out/'stage5c1_decision.json').write_text(json.dumps(payload,indent=2)); print(json.dumps(payload,indent=2))
if __name__=='__main__': main()
