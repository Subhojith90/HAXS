"""Conditional Stage 5C preflight gate. It never launches broad compute."""
import json
from pathlib import Path
import pandas as pd
OUT=Path('results/stage5c_preflight')
def main():
 OUT.mkdir(parents=True,exist_ok=True)
 local=Path('results/stage5b1R_lite/repaired_existing_v2/stage5b1R_curve_based_local_window.csv')
 nested=Path('results/stage5b1R_lite/repaired_existing_v2/stage5b1R_per_contrast_nested_uncertainty.csv')
 reasons=[]
 if not local.exists(): reasons.append('missing_curve_based_local_window')
 if not nested.exists(): reasons.append('missing_per_contrast_nested_uncertainty')
 eligible=False
 if not reasons:
  l=pd.read_csv(local); n=pd.read_csv(nested); core=n[n.contrast=='core_static_minus_mobile_plus_sd']
  if not bool(l['negative'].all()): reasons.append('local_window_not_negative')
  if len(core)!=2: reasons.append('missing_two_core_blocks')
  elif not bool(core['strict_negative'].all()): reasons.append('core_nested_gate_not_passed_in_both_blocks')
  eligible=not reasons
 payload={'stage':'stage5c_conditional_preflight','broad_stage5c_compute_allowed':False,
 'stage5c_holdout_preflight_eligible':eligible,'route':'holdout_preflight_only' if eligible else 'remain_stage5b1R_target_repair',
 'reasons':reasons or ['eligible_for_supervised_holdout_preflight_only; broad_stage5c_still_locked']}
 (OUT/'stage5c_preflight_decision.json').write_text(json.dumps(payload,indent=2))
 print(json.dumps(payload,indent=2))
if __name__=='__main__':main()
