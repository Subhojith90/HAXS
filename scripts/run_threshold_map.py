#!/usr/bin/env python
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

import argparse, yaml
from pathlib import Path
import pandas as pd
from haxs.nogo.thresholds import threshold_scan, ph_star_table
from haxs.nogo.certificates import restricted_nogo_certificate
from haxs.nogo.scaling import k_hsd_boundary_fit
from haxs.io.result_store import ensure_dir, save_dataframe, save_json
from haxs.utils.logging import append_log

ap=argparse.ArgumentParser(); ap.add_argument('--config', required=True); ap.add_argument('--out', default='results/paper_lite/threshold'); args=ap.parse_args(); out=ensure_dir(ROOT/args.out)
path=ROOT/args.config if not str(args.config).startswith('/') else Path(args.config)
raw=yaml.safe_load(Path(path).read_text())
df=threshold_scan(raw); pstar=ph_star_table(df); cert=restricted_nogo_certificate(df); scale=k_hsd_boundary_fit(df)
save_dataframe(out/'threshold_grid.csv', df, raw); save_dataframe(out/'threshold_table.csv', df, raw); save_dataframe(out/'p_h_star_table.csv', pstar, raw)
save_json(out/'threshold_certificate.json', {**cert, **scale})
ensure_dir(ROOT/'tables/paper_lite'); save_dataframe(ROOT/'tables/paper_lite/threshold_table.csv', df, raw); save_dataframe(ROOT/'tables/paper_lite/p_h_star_table.csv', pstar, raw)
unc=df.groupby(['dimension','mobile_eta','lambda_sd'], as_index=False).agg(mean_std_db=('xi2_db_min_std','mean'), n=('xi2_db_min_std','count'))
save_dataframe(ROOT/'tables/paper_lite/threshold_uncertainty_table.csv', unc, raw)
append_log(ROOT/'reproducibility/run_log.md', f'threshold map wrote {out}; rows={len(df)}')
with (ROOT/'reproducibility/command_history.sh').open('a', encoding='utf-8') as f: f.write(f'python scripts/run_threshold_map.py --config {args.config} --out {args.out}\n')
print(f'threshold map wrote {out}; rows={len(df)}')
