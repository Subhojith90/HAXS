from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_stage2_lite_configs_exist_and_parse():
    cfgs = sorted((ROOT / 'configs' / 'stage2_lite').glob('*.yaml'))
    assert len(cfgs) >= 6
    for p in cfgs:
        raw = yaml.safe_load(p.read_text())
        assert raw['level'] == 'stage2_lite'
        assert 'dtwa' in raw
        assert 'model' in raw or p.name in {'finite_size.yaml', 'runtime_scaling.yaml'}


def test_stage2_scripts_exist():
    expected = [
        'run_stage2_seed_statistics.py', 'run_stage2_finite_size.py',
        'run_stage2_mechanism_ablation.py', 'run_stage2_parameter_sweep.py',
        'run_stage2_cross_validation.py', 'run_stage2_runtime_scaling.py',
        'make_stage2_decision.py', 'run_stage2_all_lite.py'
    ]
    for name in expected:
        assert (ROOT / 'scripts' / name).exists()


def test_stage2_full_is_not_smaller_than_lite():
    lite = yaml.safe_load((ROOT/'configs/stage2_lite/seed_statistics.yaml').read_text())
    full = yaml.safe_load((ROOT/'configs/stage2_full/seed_statistics.yaml').read_text())
    assert full['stage2']['seeds'] >= lite['stage2']['seeds']
    assert full['dtwa']['n_traj'] >= lite['dtwa']['n_traj']
