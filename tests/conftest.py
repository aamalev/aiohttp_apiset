import asyncio
import os

import pytest
from aiohttp import web

from aiohttp_apiset import SwaggerRouter
from aiohttp_apiset import ApiSet
from aiohttp_apiset.swagger import ui


if not os.path.exists(ui.STATIC_UI):
    os.makedirs(ui.STATIC_UI)
    os.makedirs(os.path.dirname(ui.TEMPLATE_UI))
    with open(ui.TEMPLATE_UI, 'w'):
        pass


@pytest.fixture
def client(loop, test_client, swagger_router):
    def create_app(loop):
        app = web.Application(loop=loop, router=swagger_router)
        return app
    return loop.run_until_complete(test_client(create_app))


@asyncio.coroutine
def handler(request):
    """
    ---
    description: swagger operation
    """
    raise web.HTTPOk()


class SimpleView:

    @asyncio.coroutine
    def get(self, request):
        raise web.HTTPOk(text='simple handler get')

    @asyncio.coroutine
    def post(self):
        raise web.HTTPOk(text='simple handler post')

    @asyncio.coroutine
    def return_json(self):
        return {'status': 200}


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
    router = SwaggerRouter(
        search_dirs=['tests'],
        swagger_ui=False,
    )
    router.include('data/root.yaml')
    return router


class ViewWithInit:
    @asyncio.coroutine
    def init(self, request):
        self.request = request

    def get(self, **kwargs):
        return self.request
