import pytest

from aiohttp_apiset.parameters.converter import convert_primitive
from aiohttp_apiset.schema import Schema


@pytest.mark.parametrize('schema,input_value,expected_value', [
    (None, 'value', 'value'),
    (Schema(), 'value', 'value'),
    (Schema(type_='integer'), '1', 1),
    (Schema(type_='number'), '1.5', 1.5),
    (Schema(type_='number', format_='float'), '2.5', 2.5),
    (Schema(type_='number', format_='dobule'), '3.5', 3.5),
    (Schema(type_='number', format_='int32'), '4', 4),
    (Schema(type_='number', format_='int64'), '5', 5),
    (Schema(type_='boolean'), 'true', True),
    (Schema(type_='boolean'), 'false', False),
    (Schema(type_='boolean'), '1', True),
    (Schema(type_='boolean'), '0', False),
    (Schema(type_='null'), '', None),
    (Schema(type_='null'), 'null', None),
    (Schema(type_='string'), 'null', 'null'),
    (Schema(type_=['string', 'null']), 'null', None),
    (Schema(type_=['string', 'null']), '', None),
    (Schema(type_=['integer', 'null']), 'null', None),
    (Schema(type_=['integer', 'null']), '', None),
    (Schema(type_=['integer', 'null']), '1', 1),
    (Schema(type_=['boolean', 'null']), '', None),
    (Schema(type_=['boolean', 'null']), 'null', None),
    (Schema(type_=['boolean', 'null']), 'true', True),
])
def test_convert_primitive(schema, input_value, expected_value):
    actual_value = convert_primitive(schema, input_value)
    assert actual_value == expected_value


def test_convert_primitive_failed():
    with pytest.raises(ValueError):
        convert_primitive(Schema(type_='integer'), 'test')
    with pytest.raises(ValueError, match='Not valid value for bool: test'):
        convert_primitive(Schema(type_='boolean'), 'test')
    with pytest.raises(ValueError, match='Not valid value for null: test'):
        convert_primitive(Schema(type_='null'), 'test')
