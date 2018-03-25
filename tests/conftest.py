import pytest
from aiohttp import web

from aiohttp_apiset import SwaggerRouter
from aiohttp_apiset import ApiSet
from aiohttp_apiset.swagger import ui


if not ui.STATIC_UI.exists():
    ui.STATIC_UI.mkdir(parents=True, exist_ok=True)
    for t in ui.TEMPLATE_UI.values():
        t.parent.mkdir(parents=True, exist_ok=True)
        with t.open('a'):
            pass


@pytest.fixture
def client(loop, test_client, swagger_router):
    def create_app(loop):
        app = web.Application(loop=loop, router=swagger_router)
        return app
    return loop.run_until_complete(test_client(create_app))


async def handler(request):
    """
    ---
    description: swagger operation
    """
    raise web.HTTPOk()


class SimpleView:

    async def get(self, request):
        raise web.HTTPOk(text='simple handler get')

    async def post(self):
        raise web.HTTPOk(text='simple handler post')

    async def return_json(self):
        return {'status': 200}


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
    router = SwaggerRouter(
        search_dirs=['tests'],
        swagger_ui=False,
    )
    router.include('data/root.yaml')
    return router


class ViewWithInit:
    async def init(self, request):
        self.request = request

    def get(self, **kwargs):
        return self.request
