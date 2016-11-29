import asyncio

import pytest
import yaml
from aiohttp import hdrs, web, multidict
from aiohttp.test_utils import make_mocked_request

from aiohttp_apiset.swagger.route import SwaggerValidationRoute
from aiohttp_apiset import SwaggerRouter
from aiohttp_apiset.middlewares import jsonify


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
- name: road_id_brackets
  in: query
  required: true
  type: array
  collectionFormat: brackets
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
""")


def handler(request, road_id):
    assert road_id
    return dict(request)


@asyncio.coroutine
def test_route():
    sd = {'parameters': parameters}
    r = SwaggerValidationRoute(
        'GET', handler=handler, resource=None,
        swagger_data=sd)
    r.build_swagger_data({})
    query = ('/?road_id=1&road_id=2'
             '&road_id_csv=1,2'
             '&road_id_brackets[]=1&road_id_brackets[]=2')
    request = make_mocked_request('GET', query)
    request._match_info = {}
    resp = yield from r.handler(request)
    assert isinstance(resp, dict), resp
    assert 'road_id' in resp, resp
    assert 'road_id_csv' in resp, resp
    assert 'road_id_brackets' in resp, resp


@asyncio.coroutine
def test_json():

    def handler(request):
        assert request.content_type == 'application/json'
        assert 'jso' in request
        return dict(request)

    sd = {'parameters': parameters}
    r = SwaggerValidationRoute(
        'GET', handler=handler, resource=None,
        swagger_data=sd)
    r.build_swagger_data({})
    request = make_mocked_request(
        'POST', '/',
        headers=multidict.CIMultiDict({
            hdrs.CONTENT_TYPE: 'application/json'
        }),
    )
    request.json = asyncio.coroutine(lambda: {'f': ''})
    request._match_info = {}
    resp = yield from r.handler(request)
    assert isinstance(resp, dict), resp
    assert 'road_id' in resp, resp

    # not valid data
    request.json = asyncio.coroutine(lambda: {'f': 1})
    with pytest.raises(web.HTTPBadRequest):
        yield from r.handler(request)

    try:
        yield from r.handler(request)
    except web.HTTPBadRequest as e:
        resp = e

    assert resp.reason['jso.f'], resp.reason


@asyncio.coroutine
def test_router(test_client):
    router = SwaggerRouter()
    router.add_route(
        'POST', '/', handler,
        swagger_data={'parameters': parameters},
    ).build_swagger_data({})

    def factory(loop, *args, **kwargs):
        app = web.Application(router=router, loop=loop, middlewares=[jsonify])
        return app

    cli = yield from test_client(factory)
    query = '/?road_id=1&road_id_csv=1&road_id_brackets[]=1'
    resp = yield from cli.post(query)
    assert resp.status == 200, resp
    txt = yield from resp.text()
    assert 'road_id' in txt, txt
    assert 'road_id_csv' in txt, txt
    assert 'road_id_brackets' in txt, txt


@asyncio.coroutine
def test_router_files(test_client):
    router = SwaggerRouter(search_dirs=['tests'], default_validate=True)
    router.include('data/root.yaml')

    def factory(loop, *args, **kwargs):
        app = web.Application(router=router, loop=loop, middlewares=[jsonify])
        return app

    cli = yield from test_client(factory)
    url = router['file:simple:view'].url()

    assert isinstance(
        router['file:simple:view']._routes['POST'],
        SwaggerValidationRoute)

    resp = yield from cli.post(url + '?road_id=g')
    assert resp.status == 200, resp
