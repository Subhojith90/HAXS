from haxs.config.load import load_config
import haxs


def test_package_imports_cleanly():
    assert hasattr(haxs, '__version__')


def test_config_loading_uses_yaml_shape():
    cfg = load_config('configs/smoke/ideal_1d.yaml')
    assert cfg.lattice.shape == (10,)
    assert cfg.model.j_perp == 1.0
    assert cfg.dtwa.n_steps == 25
