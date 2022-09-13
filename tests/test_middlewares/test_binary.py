import pytest
from aiohttp import web

from aiohttp_apiset import middlewares


@pytest.mark.parametrize('data', [
    '',
    b'',
    web.HTTPOk(),
    web.Response(text='OK')
])
async def test_binary(aiohttp_client, data):
    async def handler(request):
        if isinstance(data, web.HTTPOk):
            raise data
        return data

    app = web.Application(middlewares=[middlewares.binary])
    app.router.add_get('/', handler)

    client = await aiohttp_client(app)
    rep = await client.get('/')
    assert rep.status == 200, await rep.text()
