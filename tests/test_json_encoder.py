import json
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from multidict import MultiDict

from aiohttp_apiset.errors import Errors
from aiohttp_apiset.json_encoder import JsonEncoder


def test_dumps(custom_mapping):
    multi = MultiDict()
    multi.add('k', 'v1')
    multi.add('k', 'v2')

    my = custom_mapping({'k': 'v'})
    assert len(my) == 1

    encoder = JsonEncoder.class_factory(ensure_ascii=False)

    uid = uuid4()
    now = datetime.now()
    today = date.today()
    data = encoder.dumps({
        'errors': Errors('value'),
        'multidict': multi,
        'mapping': my,
        'uuid': uid,
        'map_iter': map(lambda x: x * 2, [1, 3, 4]),
        'set': {1, 2, 3},
        'frozenset': frozenset([1, 2, 3]),
        'datetime': now,
        'date': today,
        'decimal': Decimal(1),
    })

    data = json.loads(data)
    assert data == {
        'errors': ['value'],
        'multidict': {'k': ['v1', 'v2']},
        'mapping': {'k': 'v'},
        'uuid': str(uid),
        'map_iter': [2, 6, 8],
        'set': [1, 2, 3],
        'frozenset': [1, 2, 3],
        'datetime': now.isoformat(' '),
        'date': today.isoformat(),
        'decimal': '1'
    }

    obj = object()
    obj_repr = encoder.dumps(obj)
    assert obj_repr == json.dumps(repr(obj))

    encoder.default_repr = False
    with pytest.raises(TypeError, match='not JSON serializable'):
        encoder.dumps(obj)
