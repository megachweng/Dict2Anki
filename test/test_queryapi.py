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

def test_eudict_implication():
    # 不包含图片，定义不在正常规则内，包含 trans
    res = api.query('implication')
    ret = check_result(res)
    assert set(ret) - set(['image']) == set()

def test_eudict_epitomize():
    # 不包含图片，定义不在正常规则内
    res = api.query('epitomize')
    ret = check_result(res)
    assert set(ret) - set(['image', 'phrase']) == set()

def test_eudict_periodical():
    # 包含图片，定义不在正常规则内
    res = api.query('periodical')
    ret = check_result(res)
    assert set(ret) - set(['image', 'phrase']) == set()
