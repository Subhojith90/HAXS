
from pathlib import Path
import sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'src'))
from haxs.validation.random_effects import balanced_random_effects_anova

def test_balanced_random_effects_anova_recovers_known_scales_approximately():
    rng=np.random.default_rng(123)
    I,J,K=80,5,6
    sig_occ, sig_path, sig_phase = 0.30, 0.20, 0.10
    rows=[]
    occ_eff=rng.normal(0,sig_occ,size=I)
    for i in range(I):
        path_eff=rng.normal(0,sig_path,size=J)
        for j in range(J):
            for k in range(K):
                y=-0.4+occ_eff[i]+path_eff[j]+rng.normal(0,sig_phase)
                rows.append({'occupancy_idx':i,'path_idx':j,'phase_idx':k,'effect_db':y})
    est=balanced_random_effects_anova(pd.DataFrame(rows))
    assert abs(est['mean_effect_db'] + 0.4) < 0.08
    assert abs(est['sigma2_occupancy'] - sig_occ**2) < 0.04
    assert abs(est['sigma2_path'] - sig_path**2) < 0.025
    assert abs(est['sigma2_phase_batch'] - sig_phase**2) < 0.01
    assert est['hierarchical_standard_error'] > 0
