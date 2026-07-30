#!/usr/bin/env python
import subprocess, sys
cmds=[
 ['scripts/run_stage3_seed_campaign.py','--config','configs/stage3_lite/publication_evidence.yaml','--out','results/stage3_lite/seed_campaign'],
 ['scripts/run_stage3_finite_size.py','--config','configs/stage3_lite/publication_evidence.yaml','--out','results/stage3_lite/finite_size'],
 ['scripts/run_stage3_mechanism_inference.py','--config','configs/stage3_lite/publication_evidence.yaml','--out','results/stage3_lite/mechanism_inference'],
 ['scripts/run_stage3_crossval_inference.py','--config','configs/stage3_lite/publication_evidence.yaml','--out','results/stage3_lite/crossval_inference'],
 ['scripts/make_stage3_figures.py','--results','results/stage3_lite','--out','figures/stage3_lite'],
 ['scripts/make_stage3_decision.py','--results','results/stage3_lite','--out','results/stage3_lite/decision'],
 ['scripts/make_stage3_report.py','--results','results/stage3_lite','--figures','figures/stage3_lite','--out','manuscript/stage3_lite'],
]
for c in cmds:
    print('RUN:', ' '.join([sys.executable]+c), flush=True)
    subprocess.run([sys.executable]+c, check=True)
print('Stage 3 lite complete.')
