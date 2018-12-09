import pytest

from aiohttp_apiset.swagger.loader import deref
from aiohttp_apiset.swagger.operations import OperationIdMapping

data = {
    'a': {
        'b': [
            {'$ref': '#/definitions/G'},
            3,
        ]
    }
}

spec = {
    'definitions': {
        'F': 1,
        'G': {'$ref': '#/definitions/F'}
    }
}


def test_deref():
    deref_data = deref(data, spec)
    assert deref_data is not data
    assert deref_data == {
        'a': {
            'b': [
                1,
                3,
            ]
        }
    }


def test_operation_id1():
    opmap = OperationIdMapping('math.sin')
    assert opmap


def test_operation_id2():
    with pytest.raises(ImportError):
        OperationIdMapping('math.sin.3')


def test_operation_id3():
    with pytest.raises(ValueError):
        OperationIdMapping('3')


def test_opmap_replace():
    opmap = OperationIdMapping(dict(a=1))
    assert opmap['a'] == 1
    opmap.add(dict(a=2))
    assert opmap['a'] == 2
    opmap.add(a=3)
    assert opmap['a'] == 3
