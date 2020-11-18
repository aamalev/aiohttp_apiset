import pytest
from aiohttp import web

from aiohttp_apiset import SwaggerRouter, middlewares
from aiohttp_apiset.middlewares import Jsonify, jsonify


@pytest.mark.parametrize('middlewares', [
    [],
    [jsonify],
])
async def test_spec(loop, aiohttp_client, middlewares):
    router = SwaggerRouter(
        search_dirs=['tests'],
        default_validate=True,
        swagger_ui='apidoc',
    )

    app = web.Application(
        router=router, loop=loop,
        middlewares=middlewares)

    router.include('data/root.yaml')

    cli = await aiohttp_client(app)
    spec_url = router['swagger:spec'].url_for()
    ui_url = router['swagger:ui'].url_for()

    resp = await cli.get(ui_url)
    assert resp.status == 200, (await resp.text())

    resp = await cli.get(ui_url.with_query(spec='/api/1'))
    assert resp.status == 200, (await resp.text())

    resp = await cli.get(spec_url)
    assert resp.status == 200, (await resp.text())

    resp = await cli.get(spec_url.with_query(spec='/api/1'))
    assert resp.status == 200, (await resp.text())


async def test_json(aiohttp_client):
    router = SwaggerRouter(
        search_dirs=['tests'],
        default_validate=True,
        swagger_ui=False,
    )
    router.include('data/root.yaml')

    def factory(loop, *args, **kwargs):
        app = web.Application(
            router=router, loop=loop,
            middlewares=[jsonify])
        return app

    cli = await aiohttp_client(factory)
    url = router['file:simple:view'].url()

    resp = await cli.put(url)
    assert resp.status == 200, (await resp.text())


def test_dumper():
    from datetime import datetime
    from decimal import Decimal
    from uuid import uuid4

    import multidict
    Jsonify().dumps({
        'since': datetime.now(),
        'date': datetime.now().date(),
        'uuid': uuid4(),
        'set': set(),
        'dict': dict(),
        'md': multidict.MultiDict(),
        'decimal': Decimal('1.1'),
    })


def test_repr():
    with pytest.raises(TypeError):
        Jsonify(default_repr=False).dumps({
            'x': object,
        })
    Jsonify(default_repr=True).dumps({
        'x': object,
    })


@pytest.mark.parametrize('data', [
    '',
    b'',
    web.HTTPOk(),
])
async def test_binary(aiohttp_client, data):
    async def h(request):
        return data

    def factory(loop, *args, **kwargs):
        app = web.Application(
            loop=loop,
            middlewares=[middlewares.binary])
        app.router.add_get('/', h)
        return app

    cli = await aiohttp_client(factory)
    resp = await cli.get('/')
    assert resp.status == 200, await resp.text()
