#!/usr/bin/env python
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

import shutil
from pathlib import Path
from haxs.io.hashes import write_sha256_listing
from haxs.utils.logging import append_log
base=ROOT.parent
# source archive excludes bulky duplicate archives
for name, target in [
 ('haxs_engine_full_archive', ROOT),
 ('haxs_engine_results', ROOT/'results'),
 ('haxs_engine_figures', ROOT/'figures'),
 ('haxs_engine_tables', ROOT/'tables'),
]:
    zip_base=base/name
    if Path(str(zip_base)+'.zip').exists(): Path(str(zip_base)+'.zip').unlink()
    shutil.make_archive(str(zip_base), 'zip', target)
write_sha256_listing(ROOT, ROOT/'reproducibility/sha256.txt')
append_log(ROOT/'reproducibility/run_log.md', 'archives generated')
with (ROOT/'reproducibility/command_history.sh').open('a', encoding='utf-8') as f: f.write('python scripts/make_archive.py\n')
print('archives written to', base)
