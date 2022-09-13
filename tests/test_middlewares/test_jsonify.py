import asyncio
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from aiohttp import web
from multidict import MultiDict

from aiohttp_apiset import middlewares
from aiohttp_apiset.errors import Errors
from aiohttp_apiset.validator import ValidationError


@pytest.mark.parametrize('default_repr', [True, False])
async def test_json(aiohttp_client, custom_mapping, default_repr):
    async def handler(request):
        return web.Response(text='OK')

    async def future_handler(request):
        return asyncio.create_task(handler(request))

    async def json_handler(request):
        return {
            'status': 'success',
            'errors': Errors('value'),
            'multidict': MultiDict({'k': 'v'}),
            'mapping': custom_mapping({'k': 'v'}),
            'uuid': uuid4(),
            'map_iter': map(lambda x: x * 2, [1, 3, 4]),
            'set': {1, 2, 3},
            'frozenset': frozenset([1, 2, 3]),
            'datetime': datetime.now(),
            'date': date.today(),
            'decimal': Decimal(1),
            'object': object()
        }

    async def ok_handler(request):
        raise web.HTTPOk(reason='OK')

    async def datetime_handler(request):
        return datetime.utcnow()

    async def error_handler(request):
        raise web.HTTPBadRequest(reason='test')

    async def validation_error_handler(request):
        raise ValidationError(key='value')

    json_middleware = middlewares.jsonify(default_repr=default_repr)
    app = web.Application(middlewares=[json_middleware],)
    app.router.add_get('/', handler)
    app.router.add_get('/future', future_handler)
    app.router.add_get('/json', json_handler)
    app.router.add_get('/ok', ok_handler)
    app.router.add_get('/datetime', datetime_handler)
    app.router.add_get('/error', error_handler)
    app.router.add_get('/validation-error', validation_error_handler)

    client = await aiohttp_client(app)

    rep = await client.get('/')
    assert rep.status == 200, (await rep.text())
    data = await rep.text()
    assert data == 'OK'

    rep = await client.get('/future')
    assert rep.status == 200, (await rep.text())
    data = await rep.text()
    assert data == 'OK'

    rep = await client.get('/json')
    status_code = 200 if default_repr else 500
    assert rep.status == status_code, (await rep.text())

    rep = await client.get('/ok')
    assert rep.status == 200, (await rep.text())
    data = await rep.text()
    assert data == '200: OK'

    rep = await client.get('/datetime')
    assert rep.status == 200, (await rep.text())

    rep = await client.get('/error')
    assert rep.status == 400, (await rep.text())
    data = await rep.json()
    assert data == {'error': 'test'}

    rep = await client.get('/validation-error')
    assert rep.status == 400, (await rep.text())
    data = await rep.json()
    assert data == {'errors': {'key': ['value']}}
