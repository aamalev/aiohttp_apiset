from aiohttp_apiset.openapi.schema import v2_0, v3_1


def test_model_repr():
    _assert_repr(v2_0.PathItem())
    _assert_repr(v3_1.PathItem())
    _assert_repr(v3_1.Schema(type_='object'))


def _assert_repr(obj):
    assert 'None' not in repr(obj)
