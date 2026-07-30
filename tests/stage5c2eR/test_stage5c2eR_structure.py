from pathlib import Path
import subprocess, sys, yaml
ROOT=Path(__file__).resolve().parents[2]

def test_stage5c2er_files_exist():
    for rel in [
        'pyproject.toml',
        'configs/stage5c2eR/primary_I16_J6_K4.yaml',
        'scripts/run_stage5c2eR_primary_extension.py',
        'scripts/analyze_stage5c2eR.py',
        'scripts/run_stage5c2eR_all.py',
        'scripts/verify_manifest.py',
    ]:
        assert (ROOT/rel).exists(), rel

def test_stage5c2er_config_targets_dominant_variance():
    cfg=yaml.safe_load((ROOT/'configs/stage5c2eR/primary_I16_J6_K4.yaml').read_text())['stage5c2eR']
    assert cfg['existing_design']['occupancies']==12
    assert cfg['existing_design']['paths_per_occupancy']==4
    assert cfg['extended_design']['occupancies']==16
    assert cfg['extended_design']['paths_per_occupancy']==6
    assert cfg['extended_design']['phase_batches_per_path']==4
    assert cfg['gates']['absolute_mc_se_below']==0.05

def test_domain_seed_is_stable_and_separated():
    sys.path.insert(0, str(ROOT/'scripts'))
    from stage5c2eR_common import domain_seed
    a=domain_seed('stage','primary','occupancy',1)
    b=domain_seed('stage','confirmation','occupancy',1)
    c=domain_seed('stage','primary','path',1,0)
    assert a == domain_seed('stage','primary','occupancy',1)
    assert len({a,b,c})==3

def test_patch_script_runs():
    res=subprocess.run([sys.executable,'scripts_patch/stage5c2eR_patch.py'],cwd=ROOT,text=True,capture_output=True)
    assert res.returncode==0, res.stdout+res.stderr
