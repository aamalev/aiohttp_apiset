
from aiohttp_apiset.swagger.loader import deref

data = {
    'a': {
        'b': [
            {'$ref': '#/definitions/F'},
            3,
        ]
    }
}

spec = {
    'definitions': {
        'F': 1
    }
}


def test_deref():
    deref_data, changes = deref(data, spec)
    assert changes
    assert deref_data == {
        'a': {
            'b': [
                1,
                3,
            ]
        }
    }
