import asyncio
from urllib.parse import urljoin

import pytest
from aiohttp import web

from aiohttp_apiset import SwaggerRouter
from aiohttp_apiset.middlewares import jsonify


@pytest.mark.parametrize('middlewares', [
    [],
    [jsonify],
])
@asyncio.coroutine
def test_spec(test_client, middlewares):
    router = SwaggerRouter(
        search_dirs=['tests'],
        default_validate=True,
    )
    router.include('data/root.yaml')

    def factory(loop, *args, **kwargs):
        app = web.Application(
            router=router, loop=loop,
            middlewares=middlewares)
        return app

    cli = yield from test_client(factory)
    spec_url = list(router._swagger_yaml.keys())[0]
    ui_url = urljoin(spec_url, 'index.html')

    resp = yield from cli.get(ui_url)
    assert resp.status == 200, resp

    resp = yield from cli.get(spec_url)
    assert resp.status == 200, resp


@asyncio.coroutine
def test_json(test_client):
    router = SwaggerRouter(
        search_dirs=['tests'],
        default_validate=True,
    )
    router.include('data/root.yaml')

    def factory(loop, *args, **kwargs):
        app = web.Application(
            router=router, loop=loop,
            middlewares=[jsonify])
        return app

    cli = yield from test_client(factory)
    url = cli.app.router['file:simple:view'].url()

    resp = yield from cli.put(url)
    assert resp.status == 200, resp
