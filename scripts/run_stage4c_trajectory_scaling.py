#!/usr/bin/env python
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path
import pandas as pd, yaml
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from haxs.io.result_store import ensure_dir, save_dataframe, save_json

def run(cmd):
    print('RUN:', ' '.join(map(str,cmd)), flush=True)
    subprocess.run([str(x) for x in cmd], cwd=ROOT, check=True)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--config',default='configs/stage4c_lite/trajectory_scaling.yaml')
    ap.add_argument('--out',default='results/stage4c_lite/trajectory_scaling')
    args=ap.parse_args()
    raw=yaml.safe_load((ROOT/args.config).read_text())
    out=ensure_dir(ROOT/args.out)
    cfg_dir=ensure_dir(out/'_generated_configs')
    sweep=list(raw.get('stage4c0',{}).get('n_traj_sweep',[16,64]))
    shape_rows=[]; summary=[]
    for ntraj in sweep:
        cfg=dict(raw)
        cfg['dtwa']=dict(raw.get('dtwa',{})); cfg['dtwa']['n_traj']=int(ntraj)
        cfg['stage4']=dict(raw.get('stage4',{})); cfg['stage4']['labels']=list(raw.get('stage4',{}).get('primary_pair',['static_only','mobile_plus_spin_density']))
        cfg['stage4']['seeds']=min(int(raw.get('stage4',{}).get('seeds',4)),3)
        cfg['stage4']['trajectory_reps']=min(int(raw.get('stage4',{}).get('trajectory_reps',6)),3)
        cfg_path=cfg_dir/f'trajectory_scaling_ntraj_{ntraj}.yaml'
        cfg_path.write_text(yaml.safe_dump(cfg,sort_keys=False))
        camp=out/f'campaign_ntraj_{ntraj}'
        diag=out/f'diagnosis_ntraj_{ntraj}'
        run([sys.executable,'scripts/run_stage4_publication_campaign.py','--config',str(cfg_path.relative_to(ROOT)),'--out',str(camp.relative_to(ROOT))])
        run([sys.executable,'scripts/run_stage4a_stability_diagnosis.py','--config',str(cfg_path.relative_to(ROOT)),'--campaign-dir',str(camp.relative_to(ROOT)),'--out',str(diag.relative_to(ROOT))])
        pair=pd.read_csv(camp/'stage4_primary_pair_effects.csv')
        nested=pd.read_csv(camp/'stage4_nested_uncertainty.csv')
        stability=pd.read_csv(diag/'stage4a_shape_stability_diagnosis.csv')
        primary=pair[pair.metric=='xi2_db_fixed'].copy()
        fixed_negative=int((primary.mean_effect_db<0).sum())
        fixed_ci=int(primary.ci_excludes_zero.sum())
        nested_fixed=nested[nested.metric=='xi2_db_fixed'].copy()
        traj_dom=int((nested_fixed.trajectory_fraction_of_total_variance>float(raw.get('stage4c0',{}).get('trajectory_fraction_threshold',0.5))).sum())
        stable=int(nested_fixed.nested_effect_stable.sum()) if 'nested_effect_stable' in nested_fixed.columns else 0
        summary.append({'n_traj':int(ntraj),'fixed_negative_shapes':fixed_negative,'fixed_ci_shapes':fixed_ci,'trajectory_dominated_shapes':traj_dom,'nested_stable_shapes':stable,'mean_fixed_effect_db':float(primary.mean_effect_db.mean()) if len(primary) else float('nan')})
        for _,r in stability.iterrows():
            shape_rows.append({'n_traj':int(ntraj), **{k:r[k] for k in stability.columns}})
    shape_df=pd.DataFrame(shape_rows)
    sum_df=pd.DataFrame(summary)
    save_dataframe(out/'stage4c_trajectory_scaling_shape_diagnosis.csv',shape_df,raw)
    save_dataframe(out/'stage4c_trajectory_scaling_summary.csv',sum_df,raw)
    improved=False
    if len(sum_df)>=2:
        first=sum_df.iloc[0]; last=sum_df.iloc[-1]
        improved=bool(last.trajectory_dominated_shapes <= first.trajectory_dominated_shapes and last.fixed_negative_shapes >= 2)
    save_json(out/'stage4c_trajectory_scaling_manifest.json',{'stage':'stage4c0_decision_code_repair_trajectory_scaling_preflight','config':args.config,'n_traj_sweep':sweep,'improved_or_stable_under_trajectory_scaling':improved,'final_ntraj':int(sweep[-1]),'final_fixed_negative_shapes':int(sum_df.iloc[-1].fixed_negative_shapes) if len(sum_df) else 0,'final_fixed_ci_shapes':int(sum_df.iloc[-1].fixed_ci_shapes) if len(sum_df) else 0,'final_trajectory_dominated_shapes':int(sum_df.iloc[-1].trajectory_dominated_shapes) if len(sum_df) else 0,'interpretation':'trajectory scaling preflight; not a publication claim'})
    print(f'stage4c trajectory scaling wrote {out}; final_ntraj={sweep[-1]}; improved={improved}')
if __name__=='__main__': main()
