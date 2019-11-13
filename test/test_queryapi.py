from addon.queryApi.eudict import API

api = API()

keys = ('term', 'definition', 'phrase', 'image', 'sentence', 'BrEPhonetic', 'AmEPhonetic', 'BrEPron', 'AmEPron')
def check_result(res):
    ret = []
    for key in keys:
        if not res.get(key):
            ret.append(key)
    return ret

def test_eudict_no_phrase_and_image():
    res = api.query('stint')
    ret = check_result(res)
    assert set(ret) - set(['image', 'phrase']) == set()

def test_eudict_with_all():
    res = api.query('flower')
    ret = check_result(res)
    assert set(ret) == set()

def test_eudict_with_none():
    res = api.query('asafesdf')
    ret = check_result(res)
    assert set(ret) - set(keys) == set()

def test_eudict_implication_all():
    res = api.query('implication')
    ret = check_result(res)
    assert set(ret) - set(['image']) == set()
