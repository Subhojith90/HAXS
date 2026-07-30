from haxs.validation.conservation import sz_conservation_check

def test_sz_conservation():
    assert sz_conservation_check(4)['passed']
