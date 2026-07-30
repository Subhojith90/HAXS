import pandas as pd
from haxs.io.result_store import save_dataframe


def test_generated_file_has_hash(tmp_path):
    p=tmp_path/'result.csv'
    save_dataframe(p, pd.DataFrame([{'value':1.0}]), {'seed':99})
    df=pd.read_csv(p)
    assert 'config_hash' in df.columns
