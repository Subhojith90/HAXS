#!/usr/bin/env python
"""Run C.2 holdout geometries, only after C.1 decision allows it."""
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from haxs.io.result_store import ensure_dir, save_json

def run(cmd, transcript, marker=None):
 line=' '.join(map(str,cmd)); print('RUN:',line,flush=True); transcript.append('RUN: '+line)
 if marker is not None and marker.exists(): print('SKIP existing:',marker,flush=True); return
 subprocess.run([str(x) for x in cmd],cwd=ROOT,check=True)

def make_cfg(raw,st,shape,block,seed_start):
 return {'seed':raw.get('seed',131001),'lattice':raw.get('lattice',{}),'model':raw.get('model',{}),
  'dtwa':dict(raw.get('dtwa',{}),n_traj=int(st['holdout_ntraj'])),
  'stage4':{'bootstrap_samples':int(raw['stage4'].get('bootstrap_samples',1000)),'ci':float(raw['stage4'].get('ci',0.95)),'fixed_time_fraction':float(raw['stage4'].get('fixed_time_fraction',0.65)),'trajectory_seed_stride':int(raw['stage4'].get('trajectory_seed_stride',100000)),'seed_start':int(seed_start),'seeds':int(st['seeds_per_block']),'trajectory_reps':int(st['holdout_trajectory_reps']),'labels':list(st['labels']),'matched_families':[{'family':st['holdout_family'],'shapes':[list(shape)]}],'primary_pair':list(st['core_pair']),'gates':{'min_fixed_negative_shapes':1,'min_fixed_ci_shapes':1,'min_nested_stable_shapes':1,'max_trajectory_dominated_shapes':1}}}

def main():
 p=argparse.ArgumentParser();p.add_argument('--config',default='configs/stage5c1_c2_lite/conditional_pipeline.yaml');p.add_argument('--out',default='results/stage5c1_c2_lite');p.add_argument('--dry-run',action='store_true');a=p.parse_args()
 raw=yaml.safe_load((ROOT/a.config).read_text());st=raw['stage5c1_c2'];base=ROOT/a.out; dec=json.loads((base/'stage5c1_replication_resolution/decision/stage5c1_decision.json').read_text())
 if not dec['stage5c2_holdout_preflight_allowed']:
  print('Stage 5C.2 blocked by Stage 5C.1 decision; no holdout jobs launched.'); return
 c2=ensure_dir(base/'stage5c2_holdout_preflight');gen=ensure_dir(c2/'_generated_configs'); transcript=[]
 for shape in st['holdout_shapes']:
  name='x'.join(map(str,shape))
  for block,seed in [('primary',st['holdout_primary_seed_start']),('replication',st['holdout_replication_seed_start'])]:
   cfg=make_cfg(raw,st,shape,block,seed); cp=gen/f'{name}_{block}.yaml'; cp.write_text(yaml.safe_dump(cfg,sort_keys=False))
   out=c2/f'{name}_{block}_campaign';cmd=[sys.executable,'scripts/run_stage4_publication_campaign.py','--config',str(cp.relative_to(ROOT)),'--out',str(out.relative_to(ROOT))]
   if a.dry_run: print('DRY RUN:',' '.join(map(str,cmd)))
   else: run(cmd,transcript,out/'stage4_publication_campaign_manifest.json')
 if not a.dry_run:
  (c2/'COMMAND_TRANSCRIPT_STAGE5C2.txt').write_text('\n'.join(transcript)+'\n');save_json(c2/'stage5c2_manifest.json',{'stage':'stage5c2_holdout_geometry_preflight','holdout_shapes':st['holdout_shapes'],'ntraj':int(st['holdout_ntraj']),'trajectory_reps':int(st['holdout_trajectory_reps']),'status':'completed'})
 print('Stage 5C.2 holdout preflight complete.' if not a.dry_run else 'Stage 5C.2 dry run complete.')
if __name__=='__main__':main()
