import asyncio
from collections import defaultdict
from datetime import datetime

import multidict
import pytest
import yaml
from aiohttp import hdrs, web
from aiohttp.test_utils import make_mocked_request
from aiohttp_apiset import SwaggerRouter
from aiohttp_apiset.exceptions import Errors, ValidationError
from aiohttp_apiset.middlewares import jsonify
from aiohttp_apiset.swagger.loader import Loader
from aiohttp_apiset.swagger.route import SwaggerValidationRoute
from aiohttp_apiset.swagger.validate import convert, Validator


parameters = yaml.load("""
- name: road_id
  in: query
  required: true
  type: array
  items:
    type: integer
- name: road_id_csv
  in: query
  required: true
  type: array
  collectionFormat: csv
  items:
    type: integer
- name: road_id_ssv
  in: query
  required: true
  type: array
  collectionFormat: ssv
  items:
    type: integer
- name: road_id_brackets
  in: query
  required: true
  type: array
  collectionFormat: brackets
  items:
    type: integer
- name: road_id_default_csv
  in: query
  required: true
  type: array
  collectionFormat: csv
  default: [42]
  items:
    type: integer
- name: road_id_default_brackets
  in: query
  required: true
  type: array
  collectionFormat: csv
  default: [12]
  items:
    type: integer
- name: road_id_default_multi
  in: query
  required: true
  type: array
  collectionFormat: csv
  default: [24]
  items:
    type: integer
- name: road_id_style_form
  in: query
  required: true
  style: form
  explode: false
  schema:
    type: array
    items:
      type: integer
- name: road_id_style_space
  in: query
  required: true
  style: spaceDelimited
  explode: false
  schema:
    type: array
    items:
      type: integer
- name: road_id_style_pipe
  in: query
  required: true
  style: pipeDelimited
  explode: false
  schema:
    type: array
    items:
      type: integer
- name: gt
  in: path
  required: false
  type: string
- name: qu
  in: query
  required: false
  type: string
- name: fd
  in: formData
  required: false
  type: string
- name: jso
  in: body
  required: false
  schema:
    type: object
    required: [f]
    properties:
      f:
        type: string
""", Loader)


def handler(request, road_id):
    assert road_id
    return dict(request)


async def test_route():
    sd = {'parameters': parameters}
    r = SwaggerValidationRoute(
        'GET', handler=handler, resource=None,
        swagger_data=sd)
    r.build_swagger_data(None)
    query = (
        '/'
        '?road_id=1'
        '&road_id=2'
        '&road_id_csv=1,2'
        '&road_id_ssv=1%202'
        '&road_id_style_form=1,2'
        '&road_id_style_space=1%202'
        '&road_id_style_pipe=1|2'
        '&road_id_brackets[]=1'
        '&road_id_brackets[]=2'
    )
    request = make_mocked_request('GET', query)
    request._match_info = {}
    resp = await r.handler(request)
    assert isinstance(resp, dict), resp
    assert 'road_id' in resp, resp
    assert resp.get('road_id_csv') == [1, 2], resp
    assert resp.get('road_id_ssv') == [1, 2], resp
    assert resp.get('road_id_brackets') == [1, 2], resp
    assert resp.get('road_id_default_csv') == [42], resp
    assert resp.get('road_id_default_brackets') == [12], resp
    assert resp.get('road_id_default_multi') == [24], resp
    assert resp.get('road_id_style_form') == [1, 2], resp
    assert resp.get('road_id_style_space') == [1, 2], resp
    assert resp.get('road_id_style_pipe') == [1, 2], resp


async def test_json():

    def handler(request):
        assert request.content_type == 'application/json'
        assert 'jso' in request
        return dict(request)

    sd = {'parameters': parameters}
    r = SwaggerValidationRoute(
        'GET', handler=handler, resource=None,
        swagger_data=sd)
    r.build_swagger_data(None)
    request = make_mocked_request(
        'POST', '/',
        headers=multidict.CIMultiDict({
            hdrs.CONTENT_TYPE: 'application/json'
        }),
    )
    request.json = asyncio.coroutine(lambda: {'f': ''})
    request._match_info = {}
    resp = await r.handler(request)
    assert isinstance(resp, dict), resp
    assert 'road_id' in resp, resp

    # not valid data
    request.json = asyncio.coroutine(lambda: {'f': 1})
    with pytest.raises(web.HTTPBadRequest):
        await r.handler(request)

    try:
        await r.handler(request)
    except web.HTTPBadRequest as e:
        resp = e

    assert resp['jso', 'f'], resp


async def test_router(test_client):
    router = SwaggerRouter()
    router.add_route(
        'POST', '/', handler,
        swagger_data={'parameters': parameters},
    )

    def factory(loop, *args, **kwargs):
        app = web.Application(router=router, loop=loop, middlewares=[jsonify])
        return app

    cli = await test_client(factory)
    query = '/?road_id=1&road_id_csv=1&road_id_brackets[]=1'
    resp = await cli.post(query)
    assert resp.status == 200, (await resp.text())
    txt = await resp.text()
    assert 'road_id' in txt, txt
    assert 'road_id_csv' in txt, txt
    assert 'road_id_brackets' in txt, txt


async def test_router_files(test_client):
    router = SwaggerRouter(
        search_dirs=['tests'],
        default_validate=True,
        swagger_ui=False,
    )
    router.include('data/root.yaml')

    def factory(loop, *args, **kwargs):
        app = web.Application(router=router, loop=loop, middlewares=[jsonify])
        return app

    cli = await test_client(factory)
    url = router['file:simple:view'].url()

    assert isinstance(
        router['file:simple:view']._routes['POST'],
        SwaggerValidationRoute)

    resp = await cli.post(url + '?road_id=g')
    assert resp.status == 200, (await resp.text())


@pytest.mark.parametrize('args,le,result', [
    (('name', 'true', 'boolean', None), 0, True),
    (('name', 'false', 'boolean', None), 0, False),
    (('name', '', 'boolean', None), 0, True),
    (('name', None, 'boolean', None), 1, None),
    (('name', '2s', 'string', None), 0, '2s'),
    (('name', '2s', 'integer', None), 1, None),
    (('name', ['2s'], 'number', None), 1, []),
])
def test_conv(args, le, result):
    e = Errors()
    r = convert(*args, errors=e)
    assert r == result
    assert len(e) == le, e


@Validator.converts_format('test_date', raises=ValueError)
def conv_1(value):
    if isinstance(value, str):
        return datetime.strptime(value, '%Y-%m-%d')
    yield 'only string'


@Validator.checks_format('test_errors')
def conv_2(value):
    yield '123'
    return False


@pytest.mark.parametrize('schema,value,check', [
    (
        {'type': 'string',
         'format': 'test_date'},
        '2017-01-01',
        lambda v: isinstance(v, datetime)
    ), (
        {'type': 'object',
         'properties': {
             'a': {'type': 'string',
                   'format': 'test_date'}}},
        {'a': '2017-01-01'},
        lambda v: isinstance(v['a'], datetime)
    ), (
        {'type': 'object',
         'properties': {
             'a': {'type': 'object',
                   'properties': {
                       'b': {'type': 'string',
                             'format': 'test_date'}}}}},
        {'a': {'b': '2017-01-01'}},
        lambda v: isinstance(v['a']['b'], datetime)
    ),
])
def test_validator_convert(schema, value, check):
    v = Validator(schema)
    errors = defaultdict(set)
    v = v.validate(value, errors=errors)
    assert not errors, errors
    assert check(v)


@pytest.mark.parametrize('schema,value,errs', [
    (
        {'type': 'string',
         'format': 'test_errors'},
        '', {'123'}
    ),
    (
        {'type': 'integer',
         'format': 'test_errors'},
        0, {'123'}
    ),
    (
        {'type': 'integer',
         'format': 'test_date'},
        1, {'only string'}
    ),
    (
        {'type': 'boolean',
         'format': 'test_date'},
        True, {'only string'}
    ),
])
def test_validator_check_errors(schema, value, errs):
    v = Validator(schema)
    errors = Errors()
    v.validate(value, errors=errors)
    assert errors, errors
    assert set(errors.to_tree()) == errs


def test_errors():
    e = Errors()
    e['1'].add('2', '3')
    x = e['5']['6']
    assert x is not None
    e[0].add('')
    e[8, 9].add('')
    e.add((8, 9, ''))
    e.add('4')
    assert e.to_flat() == {
        '1.2': ['3'], '.': ['4'], '0': [''], '8.9': ['']}
    assert e.to_tree() == {
        '1': {'2': ['3']}, '.': ['4'], '0': [''], '8': {'9': ['']}}
    assert e, e

    assert repr(e)

    for i in e:
        assert e[i]

    e.update(Errors('', a=['']))

    e = Errors(a='b')
    e.c.add('d')
    assert e.to_tree() == {'a': ['b'], 'c': ['d']}


async def test_bool(test_client):
    def handler(b):
        return web.json_response(b)

    r = SwaggerRouter()
    r.add_get('/', handler=handler, swagger_data={'parameters': [{
        'name': 'b',
        'in': 'query',
        'type': 'boolean',
        'default': False,
    }]})
    app = web.Application(router=r)
    client = await test_client(app)
    r = await client.get('/?b=True')
    assert r.status == 200, (await r.text())
    assert (await r.json()) is True
    r = await client.get('/?b=')
    assert r.status == 200, (await r.text())
    assert (await r.json()) is True
    r = await client.get('/?b')
    assert r.status == 200, (await r.text())
    assert (await r.json()) is True
    r = await client.get('/')
    assert r.status == 200, (await r.text())
    assert (await r.json()) is False


async def test_validation_errors_constructor(test_client):
    def handler(request):
        raise ValidationError('', r=[''], q='')

    r = SwaggerRouter()
    r.add_get('/', handler=handler)
    app = web.Application(router=r)
    client = await test_client(app)
    r = await client.get('/')
    assert r.status == 400, (await r.text())
