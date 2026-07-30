#!/usr/bin/env python
"""Run Stage 5C.1: replication-block variance resolution only.

The current Stage 5C primary campaign is used as a locked reference.  A new,
higher-statistics independent replication block is generated, then analysed
with the corrected curve-local and nested-variance diagnostics.
"""
from __future__ import annotations
import argparse, json, shutil, subprocess, sys
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from haxs.io.result_store import ensure_dir, save_json

def run(cmd, transcript, marker=None):
    line=' '.join(map(str,cmd)); print('RUN:', line, flush=True); transcript.append('RUN: '+line)
    if marker is not None and marker.exists():
        print('SKIP existing:', marker, flush=True); transcript.append('SKIP existing: '+str(marker)); return
    subprocess.run([str(x) for x in cmd], cwd=ROOT, check=True)

def stage4_config(raw, st):
    return {
      'seed': raw.get('seed', 131001), 'lattice': raw.get('lattice', {}), 'model': raw.get('model', {}),
      'dtwa': dict(raw.get('dtwa', {}), n_traj=int(st['replication_ntraj'])),
      'stage4': {
        'bootstrap_samples': int(raw['stage4'].get('bootstrap_samples',1000)),
        'ci': float(raw['stage4'].get('ci',0.95)),
        'fixed_time_fraction': float(raw['stage4'].get('fixed_time_fraction',0.65)),
        'trajectory_seed_stride': int(raw['stage4'].get('trajectory_seed_stride',100000)),
        'seed_start': int(st['replication_seed_start']), 'seeds': int(st['seeds_per_block']),
        'trajectory_reps': int(st['replication_trajectory_reps']), 'labels': list(st['labels']),
        'matched_families': [{'family':st['target_family'], 'shapes':[list(st['target_shape'])]}],
        'primary_pair': list(st['core_pair']),
        'gates': {'min_fixed_negative_shapes':1,'min_fixed_ci_shapes':1,'min_nested_stable_shapes':1,'max_trajectory_dominated_shapes':1},
      }
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--config', default='configs/stage5c1_c2_lite/conditional_pipeline.yaml')
    ap.add_argument('--out', default='results/stage5c1_c2_lite')
    ap.add_argument('--primary-reference', default='results/stage5c_target_repair_lite/primary_campaign')
    ap.add_argument('--dry-run', action='store_true')
    args=ap.parse_args()
    raw=yaml.safe_load((ROOT/args.config).read_text()); st=raw['stage5c1_c2']
    out=ensure_dir(ROOT/args.out); c1=ensure_dir(out/'stage5c1_replication_resolution'); generated=ensure_dir(c1/'_generated_configs')
    primary_ref=(ROOT/args.primary_reference).resolve()
    if not primary_ref.exists() and not args.dry_run:
        raise FileNotFoundError(f'Missing locked Stage 5C primary reference: {primary_ref}. Run Stage 5C target repair first or pass --primary-reference.')
    cfg=stage4_config(raw,st); cfg_path=generated/'stage5c1_replication_resolution.yaml'; cfg_path.write_text(yaml.safe_dump(cfg,sort_keys=False))
    replication=c1/'replication_campaign'
    transcript=[]
    cmd=[sys.executable,'scripts/run_stage4_publication_campaign.py','--config',str(cfg_path.relative_to(ROOT)),'--out',str(replication.relative_to(ROOT))]
    if args.dry_run:
        print('DRY RUN:', ' '.join(map(str,cmd))); return
    run(cmd, transcript, replication/'stage4_publication_campaign_manifest.json')
    aggregate=ensure_dir(c1/'aggregate_for_diagnostics')
    target=aggregate/'primary_campaign'
    if target.exists(): shutil.rmtree(target)
    shutil.copytree(primary_ref,target)
    target_rep=aggregate/'replication_campaign'
    if target_rep.exists(): shutil.rmtree(target_rep)
    shutil.copytree(replication,target_rep)
    diagnostics=ensure_dir(c1/'diagnostics')
    run([sys.executable,'scripts/run_stage5b1R_repair_existing_curves.py','--input',str(aggregate.relative_to(ROOT)),'--out',str(diagnostics.relative_to(ROOT))], transcript)
    run([sys.executable,'scripts/run_stage5b1R_per_contrast_uncertainty.py','--input',str(aggregate.relative_to(ROOT)),'--out',str(diagnostics.relative_to(ROOT))], transcript)
    (c1/'COMMAND_TRANSCRIPT_STAGE5C1.txt').write_text('\n'.join(transcript)+'\n')
    save_json(c1/'stage5c1_manifest.json', {'stage':'stage5c1_replication_resolution','target_shape':st['target_shape_name'],'primary_reference':str(primary_ref),'replication_ntraj':int(st['replication_ntraj']),'replication_trajectory_reps':int(st['replication_trajectory_reps']),'status':'completed'})
    print('Stage 5C.1 replication-resolution complete.')
if __name__=='__main__': main()
