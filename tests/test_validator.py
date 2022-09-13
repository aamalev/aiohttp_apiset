from datetime import datetime

import pytest

from aiohttp_apiset.validator import ValidationError, Validator


@Validator.converts_format('test_date', raises=ValueError)
def convert_datetime(value):
    if isinstance(value, str):
        return datetime.strptime(value, '%Y-%m-%d')
    yield 'only string'


@Validator.checks_format('test_errors')
def check_value_always_false(value):
    yield '123'
    return False


@Validator.checks_format('test_ok')
def check_value_always_true(value):
    return True


@pytest.mark.parametrize('schema,value,check', [
    (
        {'type': 'string', 'format': 'test_date'},
        '2017-01-01',
        lambda v: isinstance(v, datetime)
    ), (
        {'type': 'object', 'properties': {'a': {'type': 'string', 'format': 'test_date'}}},
        {'a': '2017-01-01'},
        lambda v: isinstance(v['a'], datetime)
    ), (
        {
            'type': 'object',
            'properties': {
                'a': {
                    'type': 'object',
                    'properties': {'b': {'type': 'string', 'format': 'test_date'}}
                }
            }
        },
        {'a': {'b': '2017-01-01'}},
        lambda v: isinstance(v['a']['b'], datetime)
    ),
])
def test_validator_convert(schema, value, check):
    v = Validator(schema)
    v = v.validate(value)
    assert check(v)


@pytest.mark.parametrize('schema,value,errs', [
    (
        {'type': 'string', 'format': 'test_errors'},
        '', {'123'}
    ),
    (
        {'type': 'integer', 'format': 'test_errors'},
        0, {'123'}
    ),
    (
        {'type': 'integer', 'format': 'test_date'},
        1, {'only string'}
    ),
    (
        {'type': 'boolean', 'format': 'test_date'},
        True, {'only string'}
    ),
    (
        {'type': 'number', 'format': 'float'},
        True, {'True is not of type \'number\''}
    ),
])
def test_validator_check_errors(schema, value, errs):
    v = Validator(schema)
    try:
        v.validate(value)
    except ValidationError as exc:
        assert set(exc.to_tree()) == errs
    else:
        raise AssertionError('Expects validation error')  # pragma: no cover


def test_validator_check_ok():
    v = Validator({'type': 'string', 'format': 'test_ok'})
    v.validate('value')
