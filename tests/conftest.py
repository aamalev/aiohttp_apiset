import asyncio
import pytest
from aiohttp import web

from aiohttp_apiset import SwaggerRouter
from aiohttp_apiset import ApiSet


@pytest.fixture
def app(loop):
    return web.Application(loop=loop)


@asyncio.coroutine
def handler(request):
    raise web.HTTPOk()


class SimpleView:

    @asyncio.coroutine
    def get(self, request):
        raise web.HTTPOk()

    @asyncio.coroutine
    def post(self):
        raise web.HTTPOk()


class View(ApiSet):
    swagger_ref = 'data/file.yaml'
    namespace = 'test'

    @asyncio.coroutine
    def get(self):
        raise web.HTTPOk()

    @asyncio.coroutine
    def retrieve(self, request):
        raise web.HTTPGone()


@pytest.fixture
def view():
    return View


@pytest.fixture
def swagger_router():
    return SwaggerRouter(
        path='data/root.yaml',
        search_dirs=['tests'])
