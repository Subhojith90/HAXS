import pandas as pd
from haxs.config.load import load_config
from haxs.pipeline import run_config
from haxs.optimize.splits import train_test_seeds
from haxs.methods.dtwa import run_dtwa
from haxs.lattice.graphs import hypercubic_lattice
from haxs.observables.resource_accounting import account_resources


def test_deterministic_dtwa_seed_reproduces(tmp_path):
    g = hypercubic_lattice((5,), False)
    import numpy as np
    times = np.linspace(0, 0.2, 5)
    a = run_dtwa(g, times, n_traj=16, seed=44)['data']
    b = run_dtwa(g, times, n_traj=16, seed=44)['data']
    assert np.allclose(a, b)


def test_train_test_split_has_no_overlap():
    split = train_test_seeds(123, 3, 4)
    assert not (set(split['train']) & set(split['test']))


def test_resource_accounting_bounded():
    acct = account_resources(10, [8, 8], xi2=0.7, spin_length=0.8).as_dict()
    assert 0 <= acct['postselection_probability'] <= 1
    assert acct['n_eff'] == 8
    assert acct['metrological_gain_db_resource'] >= 0


def test_run_config_writes_config_hash(tmp_path):
    cfg = load_config(overrides={'lattice': {'shape':[4]}, 'dtwa': {'n_traj': 8, 't_max': 0.2, 'n_steps': 5}})
    run = run_config(cfg, tmp_path, label='tiny')
    df = pd.read_csv(run['curve_path'])
    assert 'config_hash' in df.columns
    assert run['summary']['config_hash'] == df['config_hash'].iloc[0]
