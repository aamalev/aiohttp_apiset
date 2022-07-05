import pytest
from aiohttp import web

from aiohttp_apiset.handler import create_handler
from aiohttp_apiset.parameters.extractor import ParametersExtractor
from aiohttp_apiset.parameters.payload import PayloadReader
from aiohttp_apiset.schema import (
    Parameter,
    ParameterLocation,
    ParameterStyle,
    Schema,
)


class View(web.View):
    async def get(self):
        return web.json_response('View.get')

    async def post(self):
        return web.json_response('View.post')


class CustomView:
    async def handle(self, request):
        return web.json_response('CustomView.handle')


class InitView:
    async def init(self, request):
        self.request = request

    async def handle(self, limit):
        return web.json_response({'handler_name': 'InitView.handle', 'limit': limit})


async def handler(request, **kwargs):
    return web.json_response({'handler_name': 'handler', 'kwargs': kwargs})


async def handler_without_request(limit=None):
    return web.json_response({'handler_name': 'handler_without_request', 'limit': limit})


def sync_handler(request):
    """"""


async def test_handler(aiohttp_client):
    parameters = [
        Parameter(
            name='limit',
            location=ParameterLocation.query,
            required=False,
            allow_empty_value=False,
            style=ParameterStyle.simple,
            explode=False,
            data=Schema(type_='integer')
        )
    ]
    payload_reader = PayloadReader()
    extractor = ParametersExtractor(parameters=parameters, payload=None, payload_reader=payload_reader)

    app = web.Application()
    app.router.add_view('/c', create_handler(View, extractor))
    app.router.add_view('/c-g', create_handler('tests.test_handler.View.get', extractor))
    app.router.add_view('/cv', create_handler('tests.test_handler.CustomView.handle', extractor))
    app.router.add_view('/iv', create_handler('tests.test_handler.InitView.handle', extractor))
    app.router.add_get('/h', create_handler(handler, extractor))
    app.router.add_view('/hwr', create_handler('tests.test_handler.handler_without_request', extractor))

    with pytest.raises(TypeError, match='Handler must be async'):
        create_handler(sync_handler, extractor)

    client = await aiohttp_client(app)

    async def assert_rep(path, expected_data, method='GET', params=None):
        rep = await client.request(method, path, params=params)
        assert rep.status == 200, await rep.text()
        data = await rep.json()
        assert data == expected_data

    await assert_rep('/c', 'View.get')
    await assert_rep('/c', 'View.post', method='POST')
    await assert_rep('/c-g', 'View.get')
    await assert_rep('/c-g', 'View.post', method='POST')
    await assert_rep('/cv', 'CustomView.handle')
    await assert_rep('/iv', {'handler_name': 'InitView.handle', 'limit': None})
    await assert_rep('/h', {'handler_name': 'handler', 'kwargs': {}})
    await assert_rep('/h', {'handler_name': 'handler', 'kwargs': {'limit': 1}}, params={'limit': 1})
    await assert_rep('/hwr', {'handler_name': 'handler_without_request', 'limit': None})
    await assert_rep('/hwr', {'handler_name': 'handler_without_request', 'limit': 1}, params={'limit': 1})
