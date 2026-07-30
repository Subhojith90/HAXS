#!/usr/bin/env python
import subprocess, sys
cmds=[
 ['scripts/run_stage3a_dtwa_validation.py','--config','configs/stage3a_lite/validation_repair.yaml','--out','results/stage3a_lite/dtwa_validation'],
 ['scripts/run_stage3_seed_campaign.py','--config','configs/stage3a_lite/publication_evidence_repair.yaml','--out','results/stage3a_lite/seed_campaign'],
 ['scripts/run_stage3_mechanism_inference.py','--config','configs/stage3a_lite/publication_evidence_repair.yaml','--out','results/stage3a_lite/mechanism_inference'],
 ['scripts/run_stage3a_paired_mechanism.py','--mechanism-dir','results/stage3a_lite/mechanism_inference','--out','results/stage3a_lite/paired_mechanism'],
 ['scripts/run_stage3_crossval_inference.py','--config','configs/stage3a_lite/publication_evidence_repair.yaml','--out','results/stage3a_lite/crossval_inference'],
 ['scripts/make_stage3a_figures.py','--results','results/stage3a_lite','--out','figures/stage3a_lite'],
 ['scripts/make_stage3a_decision.py','--results','results/stage3a_lite','--out','results/stage3a_lite/decision'],
 ['scripts/make_stage3a_report.py','--results','results/stage3a_lite','--figures','figures/stage3a_lite','--out','manuscript/stage3a_lite'],
]
for c in cmds:
    print('RUN:', ' '.join([sys.executable]+c), flush=True)
    subprocess.run([sys.executable]+c, check=True)
print('Stage 3A lite complete.')
