import asyncio
from pathlib import Path

from aiohttp import web

from aiohttp_apiset import SwaggerRouter


def test_app(loop, swagger_router):
    app = web.Application(loop=loop)
    swagger_router.setup(app)


def test_search_dirs():
    d = Path(__file__).parent
    r = SwaggerRouter(d / 'data/include.yaml')
    r.add_search_dir(d)


def test_merge_spec():
    d = Path(__file__).parent
    r = SwaggerRouter(d / 'data/include.yaml', search_dirs=[d])
    r.include('data/file.yaml', basePath='/inc')


def test_routes(swagger_router: SwaggerRouter):
    paths = [route.url_for().human_repr()
             for route in swagger_router.routes()]
    assert '/api/1/file/image' in paths


def test_route_include(swagger_router: SwaggerRouter):
    paths = [route.url_for().human_repr()
             for route in swagger_router.routes()]
    assert '/api/1/include2/inc/image' in paths, paths


def test_handler(swagger_router: SwaggerRouter):
    paths = [(route.method, route.url_for().human_repr())
             for route in swagger_router.routes()]
    assert ('GET', '/api/1/include/image') in paths


@asyncio.coroutine
def test_cbv_handler_get(client, swagger_router):
    url = swagger_router['file:simple:view'].url()
    res = yield from client.get(url)
    assert (yield from res.text()) == 'simple handler get'


@asyncio.coroutine
def test_cbv_handler_post(client, swagger_router):
    url = swagger_router['file:simple:view'].url()
    res = yield from client.post(url)
    assert (yield from res.text()) == 'simple handler post'


def test_override_basePath(loop):
    router = SwaggerRouter(search_dirs=['tests'])
    web.Application(router=router, loop=loop)
    prefix = '/override'
    router.include('data/root.yaml', basePath=prefix)
    paths = [url for url in [
        route.url_for().human_repr()
        for route in router.routes()
    ] if url.startswith(prefix)]
    assert prefix in router._swagger_data
    assert paths


def test_Path():
    base = Path(__file__).parent
    router = SwaggerRouter(
        search_dirs=[base],
        swagger_ui=False,
    )
    spec = base / 'data/root.yaml'
    router.include(spec)
    assert router._swagger_data
