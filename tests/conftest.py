import pytest
from aiohttp import web

from aiohttp_apiset import SwaggerRouter
from aiohttp_apiset import ApiSet


@pytest.fixture
def app():
    return web.Application()


async def handler(request):
    raise web.HTTPOk()


class SimpleView:

    async def get(self, request):
        raise web.HTTPOk()


class View(ApiSet):
    swagger_ref = 'data/file.yaml'
    namespace = 'test'

    async def get(self):
        raise web.HTTPOk()

    async def retrieve(self, request):
        raise web.HTTPGone()


@pytest.fixture
def view():
    return View


@pytest.fixture
def swagger_router():
    return SwaggerRouter(
        path='data/root.yaml',
        search_dirs=['tests'])
