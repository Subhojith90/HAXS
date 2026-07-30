#!/usr/bin/env python
import subprocess, sys
cmds = [
['python','scripts/run_stage2_seed_statistics.py','--config','configs/stage2_lite/seed_statistics.yaml','--out','results/stage2_lite/seed_statistics'],
['python','scripts/run_stage2_finite_size.py','--config','configs/stage2_lite/finite_size.yaml','--out','results/stage2_lite/finite_size'],
['python','scripts/run_stage2_mechanism_ablation.py','--config','configs/stage2_lite/mechanism_ablation.yaml','--out','results/stage2_lite/mechanism_ablation'],
['python','scripts/run_stage2_parameter_sweep.py','--config','configs/stage2_lite/parameter_sweep.yaml','--out','results/stage2_lite/parameter_sweep'],
['python','scripts/run_stage2_cross_validation.py','--config','configs/stage2_lite/cross_validation.yaml','--out','results/stage2_lite/cross_validation'],
['python','scripts/run_stage2_runtime_scaling.py','--config','configs/stage2_lite/runtime_scaling.yaml','--out','results/stage2_lite/runtime_scaling'],
['python','scripts/make_stage2_decision.py','--results','results/stage2_lite','--out','results/stage2_lite/decision']]
for c in cmds:
    print('RUN:', ' '.join(c), flush=True)
    subprocess.check_call(c)
