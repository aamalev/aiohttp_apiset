import asyncio

import yaml
from aiohttp.test_utils import make_mocked_request
from aiohttp import web

from aiohttp_apiset.swagger.validate import validate
from aiohttp_apiset.swagger.route import SwaggerValidationRoute
from aiohttp_apiset.routes import SwaggerValidationRouter
from aiohttp_apiset.middlewares import jsonify


parameters = yaml.load("""
- name: road_id
  in: query
  required: true
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
""")


def handler(request, road_id):
    assert road_id
    return request


@asyncio.coroutine
def test_route():
    sd = {'parameters': parameters}
    r = SwaggerValidationRoute('GET', handler=handler, resource=None)
    r.set_swagger(sd)
    request = make_mocked_request('GET', '/?road_id=1&road_id=2')
    request._match_info = {}
    resp = yield from r.handler(request)
    assert isinstance(resp, dict), resp
    assert 'road_id' in resp, resp


@asyncio.coroutine
def test_router(test_client):
    router = SwaggerValidationRouter()
    router.add_route(
        'POST', '/', handler,
        swagger_data={'parameters': parameters},
    )

    def factory(loop, *args, **kwargs):
        app = web.Application(router=router, loop=loop, middlewares=[jsonify])
        return app

    cli = yield from test_client(factory)
    resp = yield from cli.post('/?road_id=1')
    assert resp.status == 200, resp
    txt = yield from resp.text()
    assert 'road_id' in txt, txt
