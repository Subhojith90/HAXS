from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[2]

def test_stage5a2_files_exist():
    assert (ROOT/'scripts/run_stage5a2_estimator_convergence_replication.py').exists()
    assert (ROOT/'scripts/run_stage5a2_all_lite.py').exists()
    assert (ROOT/'scripts/make_stage5a2_manifest.py').exists()
    assert (ROOT/'configs/stage5a2_lite/estimator_convergence_replication_3x3x2.yaml').exists()
    assert (ROOT/'configs/stage5a2_full/estimator_convergence_replication_3x3x2_full.yaml').exists()
    assert (ROOT/'docs/stage5a2/STAGE5A2_RUNBOOK.md').exists()

def test_stage5a2_lite_is_true_high_trajectory_gate():
    cfg=yaml.safe_load((ROOT/'configs/stage5a2_lite/estimator_convergence_replication_3x3x2.yaml').read_text())
    assert cfg['stage5a']['target_shape']=='3x3x2'
    assert cfg['stage5a']['ntraj_sweep']==[24,64,128]
    assert cfg['stage5a']['seeds_per_block']>=8
    assert cfg['stage5a']['trajectory_reps']>=4
    assert cfg['stage5a']['replication_seed_start'] != cfg['stage5a']['primary_seed_start']

def test_stage5a2_full_has_larger_seed_reps():
    cfg=yaml.safe_load((ROOT/'configs/stage5a2_full/estimator_convergence_replication_3x3x2_full.yaml').read_text())
    assert cfg['stage5a']['ntraj_sweep']==[24,64,128]
    assert cfg['stage5a']['seeds_per_block']>=16
    assert cfg['stage5a']['trajectory_reps']>=6

def test_stage5a2_script_has_provenance_resume_and_no_publication_claim():
    txt=(ROOT/'scripts/run_stage5a2_estimator_convergence_replication.py').read_text()
    assert 'parent_config_hash' in txt
    assert 'campaign_config_hash' in txt
    assert 'done_marker' in txt
    assert 'no publication claim' in txt

def test_stage5a2_figures_do_not_hardcode_old_threshold():
    txt=(ROOT/'scripts/make_stage5a2_figures.py').read_text()
    assert "ax.axhline(0.2" not in txt
    assert 'convergence_tolerance_db' in txt
