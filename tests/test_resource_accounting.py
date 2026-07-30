from haxs.observables.resource_accounting import account_resources, postselection_mask

def test_resource_bounds():
    mask=postselection_mask([8,9,10], min_occ=9); assert mask.tolist()==[False,True,True]
    acc=account_resources(10,[8,9,10],0.5,0.8,mask)
    assert 0 <= acc.postselection_probability <= 1
    assert acc.xi2_unconditional >= acc.xi2_conditional
