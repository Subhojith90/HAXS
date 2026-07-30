#!/usr/bin/env python
from __future__ import annotations
import argparse, json
from pathlib import Path
import pandas as pd, yaml
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(); p.add_argument('--config',default='configs/stage5c_target_repair_lite/target_repair_3x3x2.yaml'); p.add_argument('--results',default='results/stage5c_target_repair_lite'); args=p.parse_args()
 st=yaml.safe_load((ROOT/args.config).read_text())['stage5c_target_repair']; base=ROOT/args.results; d=base/'diagnostics'
 local=pd.read_csv(d/'stage5b1R_curve_based_local_window.csv'); nested=pd.read_csv(d/'stage5b1R_per_contrast_nested_uncertainty.csv')
 core=nested[nested['contrast']=='core_static_minus_mobile_plus_sd']
 comps=nested[nested['contrast'].str.startswith('component_')]
 reasons=[]
 if len(core)!=2: reasons.append('missing_two_core_blocks')
 elif not bool(core['strict_negative'].all()): reasons.append('core_target_repair_gate_not_passed')
 if not bool(local['negative'].all()): reasons.append('curve_based_local_window_not_negative')
 if len(comps) and not bool(comps['strict_negative'].all()): reasons.append('component_gates_not_all_passed')
 blocks=core.set_index('block') if len(core) else pd.DataFrame()
 if len(blocks)==2:
  delta=abs(float(blocks.loc['primary','mean_effect_db'])-float(blocks.loc['replication','mean_effect_db']))
  if delta>float(st['block_compatibility_abs_db_below']): reasons.append('core_block_incompatible')
 else: delta=None
 allowed=not reasons
 payload={
   'stage':'stage5c_target_repair_decision','target_shape':st['target_shape_name'],
   'broad_finite_size_stage5c_allowed':False,
   'next_stage_holdout_geometry_preflight_allowed':allowed,
   'route':'stage5c_holdout_geometry_preflight' if allowed else 'stage5c_target_repair_escalation_needed',
   'core_block_mean_abs_delta_db':delta,
   'reasons':reasons or ['all_target_repair_gates_passed; allowed next step is holdout geometry preflight only'],
   'claim_scope':'Target-shape estimator-controlled result only. No broad finite-size or publication claim.'}
 out=base/'decision'; out.mkdir(parents=True,exist_ok=True); (out/'stage5c_target_repair_decision.json').write_text(json.dumps(payload,indent=2)); print(json.dumps(payload,indent=2))
if __name__=='__main__': main()
