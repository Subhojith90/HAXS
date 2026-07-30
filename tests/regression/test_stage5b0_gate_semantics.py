from pathlib import Path
import importlib.util
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('stage5b0_script', ROOT/'scripts/run_stage5b0_trajectory_lock_mechanism_pilot.py')
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def test_stage5b0_block_fails_when_trajectory_fraction_high():
    row=dict(mean_fixed_effect_db=-0.4,t_ci_excludes_zero=True,bootstrap_ci_excludes_zero=True,negative_seed_fraction=1.0,trajectory_fraction=0.51,nested_effect_stable=True)
    assert mod.block_ok(row,0.7,0.5) is False
    assert 'trajectory_fraction_high' in mod.failure_reasons(row,0.7,0.5)

def test_stage5b0_block_passes_when_all_gates_pass():
    row=dict(mean_fixed_effect_db=-0.4,t_ci_excludes_zero=True,bootstrap_ci_excludes_zero=True,negative_seed_fraction=0.875,trajectory_fraction=0.42,nested_effect_stable=True)
    assert mod.block_ok(row,0.7,0.5) is True
    assert mod.failure_reasons(row,0.7,0.5)=='none'
