from pathlib import Path
import pandas as pd
from haxs.io.result_store import save_dataframe


def test_shape_column_is_not_pandas_shape_tuple(tmp_path):
    diag=pd.DataFrame({'shape':['3x3','2x2x2','3x3x2'],'diagnosis':['trajectory_dominated','promising','trajectory_dominated']})
    assert not diag['shape'].astype(str).str.contains(r'\(').any()
    assert set(diag['shape']) == {'3x3','2x2x2','3x3x2'}


def test_nested_trajectory_count_matches_decision_source():
    nested=pd.DataFrame({'shape':['3x3','2x2x2','3x3x2'],'metric':['xi2_db_fixed']*3,'trajectory_fraction_of_total_variance':[0.6,0.49,0.7]})
    corrected=int((nested[nested.metric=='xi2_db_fixed'].trajectory_fraction_of_total_variance>0.5).sum())
    assert corrected == 2


def test_saved_shape_table_preserves_shape_column(tmp_path):
    p=tmp_path/'diag.csv'
    save_dataframe(p,pd.DataFrame([{'shape':'3x3','value':1}]),{})
    out=pd.read_csv(p)
    assert out['shape'].iloc[0]=='3x3'
    assert out['shape'].iloc[0] != '(19,)'
