import datetime
import uuid

import pytest

from aiohttp_apiset.config.operation import OperationIdMapping


def handler():
    """"""


def test_operation_id_mapping():
    mapping = OperationIdMapping(
        'uuid',
        datetime,
        my_operation=handler
    )
    assert len(mapping) == 3
    assert mapping['my_operation'] is handler
    assert mapping['datetime'] is datetime.datetime
    assert mapping['uuid4'] is uuid.uuid4

    with pytest.raises(KeyError):
        mapping['unknown_operation']

    with pytest.raises(NotImplementedError):
        iter(mapping)

    with pytest.raises(ImportError):
        mapping.add('unknown_package.unknown_module')

    with pytest.raises(ImportError):
        mapping.add('datetime.unknown_module')
