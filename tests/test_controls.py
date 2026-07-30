import numpy as np
from haxs.models.controls import ControlProtocol, apply_echo_x, CONTROL_CLASSIFICATION

def test_echo_flip():
    s=np.array([[[0.5,0.2,-0.1]]]); out=apply_echo_x(s)
    assert out[0,0,0]==0.5 and out[0,0,1]==-0.2 and out[0,0,2]==0.1

def test_jz_ramp():
    c=ControlProtocol(enabled=True,jz_initial=0.0,jz_final=1.0,ramp_duration=2.0)
    assert abs(c.jz_at(1.0)-0.5)<1e-12
    assert CONTROL_CLASSIFICATION['echo']=='MVP plausible'
