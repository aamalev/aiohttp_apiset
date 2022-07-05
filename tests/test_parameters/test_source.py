from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import pytest
from aiohttp import web

from aiohttp_apiset.parameters.source import (
    contains_parameter,
    get_source,
    read_value,
)
from aiohttp_apiset.schema import (
    Parameter,
    ParameterLocation,
    ParameterStyle,
    Schema,
)


@dataclass
class Value:
    raw: str
    expected: Any
    parameter: Parameter


VALUES = [
    Value(
        raw='test=1',
        expected=1,
        parameter=Parameter(
            name='test',
            location=ParameterLocation.query,
            required=True,
            allow_empty_value=False,
            style=ParameterStyle.form,
            explode=False,
            data=Schema(type_='integer')
        )
    ),
    Value(
        raw='test=null',
        expected=None,
        parameter=Parameter(
            name='test',
            location=ParameterLocation.query,
            required=True,
            allow_empty_value=False,
            style=ParameterStyle.form,
            explode=False,
            data=Schema(type_=['integer', 'null'])
        )
    ),
    Value(
        raw='test=1',
        expected=1,
        parameter=Parameter(
            name='test',
            location=ParameterLocation.query,
            required=True,
            allow_empty_value=False,
            style=ParameterStyle.form,
            explode=False,
            data=Schema(type_=['integer', 'null'])
        )
    ),
    Value(
        raw='test=2',
        expected=2,
        parameter=Parameter(
            name='test',
            location=ParameterLocation.query,
            required=True,
            allow_empty_value=False,
            style=ParameterStyle.form,
            explode=False,
            data=Schema(
                type_=['integer', 'object'],
                properties={'key': Schema(type_='string')}
            )
        )
    ),
    Value(
        raw='test=key,value',
        expected={'key': 'value'},
        parameter=Parameter(
            name='test',
            location=ParameterLocation.query,
            required=True,
            allow_empty_value=False,
            style=ParameterStyle.form,
            explode=False,
            data=Schema(
                type_=['integer', 'object'],
                properties={'key': Schema(type_='string')}
            )
        )
    ),
    Value(
        raw='true',
        expected=True,
        parameter=Parameter(
            name='test',
            location=ParameterLocation.path,
            required=True,
            allow_empty_value=False,
            style=ParameterStyle.form,
            explode=False,
            data=Schema(type_='boolean')
        )
    ),
    Value(
        raw='value',
        expected='value',
        parameter=Parameter(
            name='test',
            location=ParameterLocation.cookie,
            required=True,
            allow_empty_value=False,
            style=ParameterStyle.form,
            explode=False,
            data=Schema(type_='string')
        )
    ),
    Value(
        raw='null',
        expected=None,
        parameter=Parameter(
            name='test',
            location=ParameterLocation.header,
            required=True,
            allow_empty_value=False,
            style=ParameterStyle.form,
            explode=False,
            data=Schema(type_='null')
        )
    ),
    Value(
        raw='test=raw',
        expected='raw',
        parameter=Parameter(
            name='test',
            location=ParameterLocation.query,
            required=True,
            allow_empty_value=False,
            style=ParameterStyle.form,
            explode=False
        )
    ),
    Value(
        raw='.label',
        expected='label',
        parameter=Parameter(
            name='test',
            location=ParameterLocation.path,
            required=True,
            allow_empty_value=False,
            style=ParameterStyle.label,
            explode=False,
            data=Schema(type_='string')
        )
    ),
    Value(
        raw=';test=matrix',
        expected='matrix',
        parameter=Parameter(
            name='test',
            location=ParameterLocation.path,
            required=True,
            allow_empty_value=False,
            style=ParameterStyle.matrix,
            explode=False,
            data=Schema(type_='string')
        )
    ),
    Value(
        raw='3,4,5',
        expected=[3, 4, 5],
        parameter=Parameter(
            name='test',
            location=ParameterLocation.path,
            required=True,
            allow_empty_value=False,
            style=ParameterStyle.simple,
            explode=False,
            data=Schema(type_='array', items=Schema(type_='integer'))
        )
    ),
    Value(
        raw='3,4,5',
        expected=[3, 4, 5],
        parameter=Parameter(
            name='test',
            location=ParameterLocation.path,
            required=True,
            allow_empty_value=False,
            style=ParameterStyle.simple,
            explode=True,
            data=Schema(type_='array', items=Schema(type_='integer'))
        )
    ),
    Value(
        raw='.3.4.5',
        expected=[3, 4, 5],
        parameter=Parameter(
            name='test',
            location=ParameterLocation.path,
            required=True,
            allow_empty_value=False,
            style=ParameterStyle.label,
            explode=False,
            data=Schema(type_='array', items=Schema(type_='integer'))
        )
    ),
    Value(
        raw='.3.4.5',
        expected=[3, 4, 5],
        parameter=Parameter(
            name='test',
            location=ParameterLocation.path,
            required=True,
            allow_empty_value=False,
            style=ParameterStyle.label,
            explode=True,
            data=Schema(type_='array', items=Schema(type_='integer'))
        )
    ),
    Value(
        raw=';test=3,4,5',
        expected=[3, 4, 5],
        parameter=Parameter(
            name='test',
            location=ParameterLocation.path,
            required=True,
            allow_empty_value=False,
            style=ParameterStyle.matrix,
            explode=False,
            data=Schema(type_='array', items=Schema(type_='integer'))
        )
    ),
    Value(
        raw=';test=3;test=4;test=5',
        expected=[3, 4, 5],
        parameter=Parameter(
            name='test',
            location=ParameterLocation.path,
            required=True,
            allow_empty_value=False,
            style=ParameterStyle.matrix,
            explode=True,
            data=Schema(type_='array', items=Schema(type_='integer'))
        )
    ),
    Value(
        raw='role,admin,firstName,Alex',
        expected={'role': 'admin', 'firstName': 'Alex'},
        parameter=Parameter(
            name='test',
            location=ParameterLocation.path,
            required=True,
            allow_empty_value=False,
            style=ParameterStyle.simple,
            explode=False,
            data=Schema(type_='object', properties={
                'role': Schema(type_='string'),
                'firstName': Schema(type_='string'),
            })
        )
    ),
    Value(
        raw='role=admin,firstName=Alex',
        expected={'role': 'admin', 'firstName': 'Alex'},
        parameter=Parameter(
            name='test',
            location=ParameterLocation.path,
            required=True,
            allow_empty_value=False,
            style=ParameterStyle.simple,
            explode=True,
            data=Schema(type_='object', properties={
                'role': Schema(type_='string'),
                'firstName': Schema(type_='string'),
            })
        )
    ),
    Value(
        raw='.role.admin.firstName.Alex',
        expected={'role': 'admin', 'firstName': 'Alex'},
        parameter=Parameter(
            name='test',
            location=ParameterLocation.path,
            required=True,
            allow_empty_value=False,
            style=ParameterStyle.label,
            explode=False,
            data=Schema(type_='object', properties={
                'role': Schema(type_='string'),
                'firstName': Schema(type_='string'),
            })
        )
    ),
    Value(
        raw='.role=admin.firstName=Alex',
        expected={'role': 'admin', 'firstName': 'Alex'},
        parameter=Parameter(
            name='test',
            location=ParameterLocation.path,
            required=True,
            allow_empty_value=False,
            style=ParameterStyle.label,
            explode=True,
            data=Schema(type_='object', properties={
                'role': Schema(type_='string'),
                'firstName': Schema(type_='string'),
            })
        )
    ),
    Value(
        raw=';test=role,admin,firstName,Alex',
        expected={'role': 'admin', 'firstName': 'Alex'},
        parameter=Parameter(
            name='test',
            location=ParameterLocation.path,
            required=True,
            allow_empty_value=False,
            style=ParameterStyle.matrix,
            explode=False,
            data=Schema(type_='object', properties={
                'role': Schema(type_='string'),
                'firstName': Schema(type_='string'),
            })
        )
    ),
    Value(
        raw=';role=admin;firstName=Alex',
        expected={'role': 'admin', 'firstName': 'Alex'},
        parameter=Parameter(
            name='test',
            location=ParameterLocation.path,
            required=True,
            allow_empty_value=False,
            style=ParameterStyle.matrix,
            explode=True,
            data=Schema(type_='object', properties={
                'role': Schema(type_='string'),
                'firstName': Schema(type_='string'),
            })
        )
    ),
    Value(
        raw='test=3&test=4&test=5',
        expected=[3, 4, 5],
        parameter=Parameter(
            name='test',
            location=ParameterLocation.query,
            required=True,
            allow_empty_value=False,
            style=ParameterStyle.form,
            explode=True,
            data=Schema(type_='array', items=Schema(type_='integer'))
        )
    ),
    Value(
        raw='test=3,4,5',
        expected=[3, 4, 5],
        parameter=Parameter(
            name='test',
            location=ParameterLocation.query,
            required=True,
            allow_empty_value=False,
            style=ParameterStyle.form,
            explode=False,
            data=Schema(type_='array', items=Schema(type_='integer'))
        )
    ),
    Value(
        raw='test=3&test=4&test=5',
        expected=[3, 4, 5],
        parameter=Parameter(
            name='test',
            location=ParameterLocation.query,
            required=True,
            allow_empty_value=False,
            style=ParameterStyle.space_delimited,
            explode=True,
            data=Schema(type_='array', items=Schema(type_='integer'))
        )
    ),
    Value(
        raw='test=3%204%205',
        expected=[3, 4, 5],
        parameter=Parameter(
            name='test',
            location=ParameterLocation.query,
            required=True,
            allow_empty_value=False,
            style=ParameterStyle.space_delimited,
            explode=False,
            data=Schema(type_='array', items=Schema(type_='integer'))
        )
    ),
    Value(
        raw='test=3&test=4&test=5',
        expected=[3, 4, 5],
        parameter=Parameter(
            name='test',
            location=ParameterLocation.query,
            required=True,
            allow_empty_value=False,
            style=ParameterStyle.pipe_delimited,
            explode=True,
            data=Schema(type_='array', items=Schema(type_='integer'))
        )
    ),
    Value(
        raw='test=3|4|5',
        expected=[3, 4, 5],
        parameter=Parameter(
            name='test',
            location=ParameterLocation.query,
            required=True,
            allow_empty_value=False,
            style=ParameterStyle.pipe_delimited,
            explode=False,
            data=Schema(type_='array', items=Schema(type_='integer'))
        )
    ),
    Value(
        raw='test=3&test=4&test=5',
        expected=[3, 4, 5],
        parameter=Parameter(
            name='test',
            location=ParameterLocation.query,
            required=True,
            allow_empty_value=False,
            style=ParameterStyle.tab_delimited,
            explode=True,
            data=Schema(type_='array', items=Schema(type_='integer'))
        )
    ),
    Value(
        raw='test=3%094%095',
        expected=[3, 4, 5],
        parameter=Parameter(
            name='test',
            location=ParameterLocation.query,
            required=True,
            allow_empty_value=False,
            style=ParameterStyle.tab_delimited,
            explode=False,
            data=Schema(type_='array', items=Schema(type_='integer'))
        )
    ),
    Value(
        raw='test=',
        expected=None,
        parameter=Parameter(
            name='test',
            location=ParameterLocation.query,
            required=False,
            allow_empty_value=True,
            style=ParameterStyle.simple,
            explode=False,
            data=Schema(type_='array', items=Schema(type_='integer'))
        )
    ),
    Value(
        raw='test=',
        expected=None,
        parameter=Parameter(
            name='test',
            location=ParameterLocation.query,
            required=False,
            allow_empty_value=True,
            style=ParameterStyle.simple,
            explode=True,
            data=Schema(type_='array', items=Schema(type_='integer'))
        )
    ),
    Value(
        raw='test=role,admin,firstName,Alex',
        expected={'role': 'admin', 'firstName': 'Alex'},
        parameter=Parameter(
            name='test',
            location=ParameterLocation.query,
            required=True,
            allow_empty_value=False,
            style=ParameterStyle.form,
            explode=False,
            data=Schema(type_='object', properties={
                'role': Schema(type_='string'),
                'firstName': Schema(type_='string'),
            })
        )
    ),
    Value(
        raw='test[role]=admin&test[firstName]=Alex',
        expected={'role': 'admin', 'firstName': 'Alex'},
        parameter=Parameter(
            name='test',
            location=ParameterLocation.query,
            required=True,
            allow_empty_value=False,
            style=ParameterStyle.deep_object,
            explode=True,
            data=Schema(type_='object', properties={
                'role': Schema(type_='string'),
                'firstName': Schema(type_='string'),
            })
        )
    ),
    Value(
        raw='role=admin&firstName=Alex',
        expected={'role': 'admin', 'firstName': 'Alex'},
        parameter=Parameter(
            name='test',
            location=ParameterLocation.query,
            required=True,
            allow_empty_value=False,
            style=ParameterStyle.form,
            explode=True,
            data=Schema(type_='object', properties={
                'role': Schema(type_='string'),
                'firstName': Schema(type_='string'),
            })
        )
    ),
    Value(
        raw='role=admin',
        expected={'role': 'admin'},
        parameter=Parameter(
            name='test',
            location=ParameterLocation.query,
            required=True,
            allow_empty_value=False,
            style=ParameterStyle.form,
            explode=True,
            data=Schema(
                type_='object',
                properties={
                    'role': Schema(type_='string'),
                    'firstName': Schema(type_='string'),
                },
                required=['role']
            )
        )
    ),
    Value(
        raw='role=',
        expected={'role': ''},
        parameter=Parameter(
            name='test',
            location=ParameterLocation.query,
            required=True,
            allow_empty_value=False,
            style=ParameterStyle.form,
            explode=True,
            data=Schema(
                type_=['object', 'string'],
                properties={
                    'role': Schema(type_='string'),
                    'firstName': Schema(type_='string'),
                },
                required=['role']
            )
        )
    ),
    Value(
        raw='test=',
        expected='',
        parameter=Parameter(
            name='test',
            location=ParameterLocation.query,
            required=True,
            allow_empty_value=False,
            style=ParameterStyle.form,
            explode=True
        )
    ),
    Value(
        raw='3,4,5',
        expected=[3, 4, 5],
        parameter=Parameter(
            name='test',
            location=ParameterLocation.header,
            required=False,
            allow_empty_value=True,
            style=ParameterStyle.simple,
            explode=False,
            data=Schema(type_='array', items=Schema(type_='integer'))
        )
    ),
    Value(
        raw='3,4,5',
        expected=[3, 4, 5],
        parameter=Parameter(
            name='test',
            location=ParameterLocation.header,
            required=False,
            allow_empty_value=True,
            style=ParameterStyle.simple,
            explode=True,
            data=Schema(type_='array', items=Schema(type_='integer'))
        )
    ),
    Value(
        raw='role,admin,firstName,Alex',
        expected={'role': 'admin', 'firstName': 'Alex'},
        parameter=Parameter(
            name='test',
            location=ParameterLocation.header,
            required=True,
            allow_empty_value=False,
            style=ParameterStyle.simple,
            explode=False,
            data=Schema(type_='object', properties={
                'role': Schema(type_='string'),
                'firstName': Schema(type_='string'),
            })
        )
    ),
    Value(
        raw='role=admin,firstName=Alex',
        expected={'role': 'admin', 'firstName': 'Alex'},
        parameter=Parameter(
            name='test',
            location=ParameterLocation.header,
            required=True,
            allow_empty_value=False,
            style=ParameterStyle.simple,
            explode=True,
            data=Schema(type_='object', properties={
                'role': Schema(type_='string'),
                'firstName': Schema(type_='string'),
            })
        )
    ),
    Value(
        raw='3,4,5',
        expected=[3, 4, 5],
        parameter=Parameter(
            name='test',
            location=ParameterLocation.cookie,
            required=False,
            allow_empty_value=True,
            style=ParameterStyle.form,
            explode=False,
            data=Schema(type_='array', items=Schema(type_='integer'))
        )
    ),
    Value(
        raw='role,admin,firstName,Alex',
        expected={'role': 'admin', 'firstName': 'Alex'},
        parameter=Parameter(
            name='test',
            location=ParameterLocation.cookie,
            required=True,
            allow_empty_value=False,
            style=ParameterStyle.form,
            explode=False,
            data=Schema(type_='object', properties={
                'role': Schema(type_='string'),
                'firstName': Schema(type_='string'),
            })
        )
    ),
    Value(
        raw='test={"role": "admin", "firstName": "Alex"}',
        expected={'role': 'admin', 'firstName': 'Alex'},
        parameter=Parameter(
            name='test',
            location=ParameterLocation.query,
            required=True,
            allow_empty_value=False,
            style=ParameterStyle.json,
            explode=False,
            data=Schema(type_='object', properties={
                'role': Schema(type_='string'),
                'firstName': Schema(type_='string'),
            })
        )
    ),
    Value(
        raw='test={}'.format(quote('{"role": "admin", "firstName": "Alex"}')),
        expected={'role': 'admin', 'firstName': 'Alex'},
        parameter=Parameter(
            name='test',
            location=ParameterLocation.query,
            required=True,
            allow_empty_value=False,
            style=ParameterStyle.json,
            explode=False,
            data=Schema(type_='object', properties={
                'role': Schema(type_='string'),
                'firstName': Schema(type_='string'),
            })
        )
    ),
]


@pytest.mark.parametrize('value', VALUES)
async def test_source(aiohttp_client, value):
    async def handler(request):
        source = get_source(request, value.parameter.location)
        assert contains_parameter(source, value.parameter)
        obj = read_value(source, value.parameter)
        return web.json_response({'value': obj})

    app = web.Application()
    app.router.add_get('/', handler)
    app.router.add_get('/{test}', handler)
    client = await aiohttp_client(app)
    headers = {}
    if value.parameter.location == ParameterLocation.cookie:
        url = '/'
        cookies = {}
        cookies[value.parameter.name] = value.raw
        client.session.cookie_jar.update_cookies(cookies)
    elif value.parameter.location == ParameterLocation.header:
        url = '/'
        headers[value.parameter.name] = value.raw
    elif value.parameter.location == ParameterLocation.path:
        url = '/{}'.format(value.raw)
    else:
        assert value.parameter.location == ParameterLocation.query
        url = '/?{}'.format(value.raw)

    rep = await client.get(url, headers=headers)
    assert rep.status == 200, (await rep.text())
    data = await rep.json()
    assert data['value'] == value.expected


@pytest.mark.parametrize('value', [
    Value(
        raw='test',
        expected=r'Not valid value for bool: test|invalid literal for int\(\) with base 10\: \'test\'',
        parameter=Parameter(
            name='test',
            location=ParameterLocation.query,
            style=ParameterStyle.simple,
            explode=False,
            allow_empty_value=False,
            required=True,
            data=Schema(
                type_=['array', 'boolean'],
                items=Schema(type_='integer')
            )
        )
    )
])
def test_raises_value_error(value):
    source = {}
    source[value.parameter.name] = value.raw
    with pytest.raises(ValueError, match=value.expected):
        read_value(source, value.parameter)
    with pytest.raises(ValueError, match='Parameter {} not found'.format(value.parameter.name)):
        read_value({}, value.parameter)


def test_object_without_properties():
    parameter = Parameter(
        name='test',
        location=ParameterLocation.query,
        style=ParameterStyle.form,
        explode=False,
        allow_empty_value=False,
        required=True,
        data=Schema(
            type_='object',
        )
    )
    source = {'test': 'k,v'}
    assert contains_parameter(source, parameter)
    obj = read_value(source, parameter)
    assert obj == {'k': 'v'}

    assert not contains_parameter({'k': 'v'}, parameter)

    parameter = Parameter(
        name='test',
        location=ParameterLocation.query,
        style=ParameterStyle.form,
        explode=True,
        allow_empty_value=False,
        required=True,
        data=Schema(
            type_='object',
        )
    )
    assert not contains_parameter({'k': 'v'}, parameter)
    with pytest.raises(ValueError, match='Parameter test not found'):
        read_value({'k': 'v'}, parameter)


def test_object_with_defaults():
    parameter = Parameter(
        name='test',
        location=ParameterLocation.query,
        style=ParameterStyle.form,
        explode=False,
        allow_empty_value=False,
        required=True,
        data=Schema(
            type_='object',
            properties={
                'k': Schema(
                    type_='string',
                    default='value'
                )
            }
        )
    )
    source = {'test': ''}
    assert contains_parameter(source, parameter)
    obj = read_value(source, parameter)
    assert obj == {'k': 'value'}
