#!/usr/bin/env python
"""Stage 5C target-repair campaign.
This is a new gated execution stage, not broad finite-size Stage 5C.
It reruns the registered 3x3x2 target with corrected diagnostics built in.
"""
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path
import pandas as pd, yaml
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from haxs.io.result_store import ensure_dir, save_json

def run(cmd, transcript, marker=None):
    line=' '.join(map(str,cmd)); print('RUN:',line,flush=True); transcript.append('RUN: '+line)
    if marker is not None and marker.exists():
        print('SKIP existing:',marker,flush=True); transcript.append('SKIP existing: '+str(marker)); return
    subprocess.run([str(x) for x in cmd],cwd=ROOT,check=True)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--config',default='configs/stage5c_target_repair_lite/target_repair_3x3x2.yaml')
    ap.add_argument('--out',default='results/stage5c_target_repair_lite')
    ap.add_argument('--dry-run',action='store_true')
    args=ap.parse_args()
    raw=yaml.safe_load((ROOT/args.config).read_text())
    st=raw['stage5c_target_repair']; out=ensure_dir(ROOT/args.out)
    generated=ensure_dir(out/'_generated_configs'); transcript=[]
    for block,seed_start in st['block_seed_starts'].items():
        stage4={
          'bootstrap_samples': int(raw['stage4'].get('bootstrap_samples',1000)),
          'ci': float(raw['stage4'].get('ci',0.95)),
          'fixed_time_fraction': float(raw['stage4'].get('fixed_time_fraction',0.65)),
          'trajectory_seed_stride': int(raw['stage4'].get('trajectory_seed_stride',100000)),
          'seed_start': int(seed_start), 'seeds': int(st['seeds_per_block']),
          'trajectory_reps': int(st['trajectory_reps']), 'labels': list(st['labels']),
          'matched_families':[{'family':st['target_family'],'shapes':[list(st['target_shape'])]}],
          'primary_pair': list(st['core_pair']),
          'gates':{'min_fixed_negative_shapes':1,'min_fixed_ci_shapes':1,'min_nested_stable_shapes':1,'max_trajectory_dominated_shapes':1},
        }
        cfg={'seed':raw.get('seed',131001),'lattice':raw.get('lattice',{}),'model':raw.get('model',{}),
             'dtwa':dict(raw.get('dtwa',{}),n_traj=int(st['ntraj'])),'stage4':stage4}
        cfg_path=generated/f'stage5c_target_repair_{block}.yaml'; cfg_path.write_text(yaml.safe_dump(cfg,sort_keys=False))
        campaign=out/f'{block}_campaign'
        cmd=[sys.executable,'scripts/run_stage4_publication_campaign.py','--config',str(cfg_path.relative_to(ROOT)),'--out',str(campaign.relative_to(ROOT))]
        if args.dry_run: print('DRY RUN:', ' '.join(map(str,cmd))); transcript.append('DRY RUN: '+' '.join(map(str,cmd)))
        else: run(cmd,transcript,campaign/'stage4_publication_campaign_manifest.json')
    if not args.dry_run:
        diagnostics=out/'diagnostics'
        run([sys.executable,'scripts/run_stage5b1R_repair_existing_curves.py','--input',str(out.relative_to(ROOT)),'--out',str(diagnostics.relative_to(ROOT))],transcript)
        run([sys.executable,'scripts/run_stage5b1R_per_contrast_uncertainty.py','--input',str(out.relative_to(ROOT)),'--out',str(diagnostics.relative_to(ROOT))],transcript)
    (out/'COMMAND_TRANSCRIPT_STAGE5C_TARGET_REPAIR.txt').write_text('\n'.join(transcript)+'\n')
    save_json(out/'stage5c_target_repair_manifest.json',{
      'stage':'stage5c_target_repair','scope':st['claim_scope'],'broad_finite_size_compute_allowed':False,
      'target_shape':st['target_shape_name'],'ntraj':int(st['ntraj']),'trajectory_reps':int(st['trajectory_reps']),
      'seeds_per_block':int(st['seeds_per_block']),'labels':st['labels'],
      'control_label':'full_controlled','full_uncontrolled_reference':'mobile_plus_spin_density',
      'status':'dry_run' if args.dry_run else 'completed_target_repair_campaign'})
    print('Stage 5C target-repair complete.' if not args.dry_run else 'Stage 5C target-repair dry run complete.')
if __name__=='__main__': main()
