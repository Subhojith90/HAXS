import pandas as pd
from haxs.optimize.splits import train_test_seeds
from haxs.io.result_store import save_dataframe
from haxs.io.hashes import hash_dict

def test_split_no_overlap():
    sp=train_test_seeds(1,3,4); assert not (set(sp['train']) & set(sp['test']))

def test_save_dataframe_config_hash(tmp_path):
    p=tmp_path/'x.csv'; save_dataframe(p,pd.DataFrame([{'a':1}]),{'seed':1})
    df=pd.read_csv(p); assert 'config_hash' in df.columns

def test_hash_dict_deterministic():
    assert hash_dict({'a':1,'b':2}) == hash_dict({'b':2,'a':1})
