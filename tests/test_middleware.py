import asyncio

import pytest
from aiohttp import web

from aiohttp_apiset import SwaggerRouter
from aiohttp_apiset.middlewares import jsonify, Jsonify


@pytest.mark.parametrize('middlewares', [
    [],
    [jsonify],
])
@asyncio.coroutine
def test_spec(loop, test_client, middlewares):
    router = SwaggerRouter(
        search_dirs=['tests'],
        default_validate=True,
        swagger_ui='apidoc',
    )

    app = web.Application(
        router=router, loop=loop,
        middlewares=middlewares)

    router.include('data/root.yaml')

    cli = yield from test_client(app)
    spec_url = router['swagger:spec'].url_for()
    ui_url = router['swagger:ui'].url_for()

    resp = yield from cli.get(ui_url)
    assert resp.status == 200, resp

    resp = yield from cli.get(ui_url.with_query(spec='/api/1'))
    assert resp.status == 200, resp

    resp = yield from cli.get(spec_url)
    assert resp.status == 200, resp

    resp = yield from cli.get(spec_url.with_query(spec='/api/1'))
    assert resp.status == 200, resp


@asyncio.coroutine
def test_json(test_client):
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

    cli = yield from test_client(factory)
    url = router['file:simple:view'].url()

    resp = yield from cli.put(url)
    assert resp.status == 200, resp


def test_dumper():
    from datetime import datetime
    from uuid import uuid4
    import multidict
    from decimal import Decimal
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
