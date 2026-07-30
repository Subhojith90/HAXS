#!/usr/bin/env python
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

import subprocess, os
out = ROOT / 'reproducibility' / 'test_transcript.txt'
out.parent.mkdir(parents=True, exist_ok=True)
cmd = [sys.executable, '-m', 'pytest', 'tests', '-q']
env = os.environ.copy(); env['PYTHONPATH'] = str(ROOT / 'src')
proc = subprocess.run(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
text = '$ ' + ' '.join(cmd) + '\n' + proc.stdout
out.write_text(text, encoding='utf-8')
print(proc.stdout)
with (ROOT / 'reproducibility' / 'command_history.sh').open('a', encoding='utf-8') as f:
    f.write('python scripts/run_tests.py\n')
raise SystemExit(proc.returncode)
