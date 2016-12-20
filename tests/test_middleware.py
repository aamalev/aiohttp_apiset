import asyncio
from urllib.parse import urljoin

import pytest
from aiohttp import web

from aiohttp_apiset import SwaggerRouter
from aiohttp_apiset.middlewares import jsonify, JsonEncoder


@pytest.mark.parametrize('middlewares', [
    [],
    [jsonify],
])
@asyncio.coroutine
def test_spec(loop, test_client, middlewares):
    router = SwaggerRouter(
        search_dirs=['tests'],
        default_validate=True,
    )

    app = web.Application(
        router=router, loop=loop,
        middlewares=middlewares)

    def factory(loop, *args, **kwargs):
        return app

    router.include('data/root.yaml')

    cli = yield from test_client(factory)
    spec_url = list(router._swagger_yaml.keys())[0]
    ui_url = urljoin(spec_url, 'index.html')

    resp = yield from cli.get(ui_url)
    assert resp.status == 200, resp

    resp = yield from cli.get(spec_url)
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
    from aiohttp import multidict
    JsonEncoder.dumps({
        'since': datetime.now(),
        'date': datetime.now().date(),
        'uuid': uuid4(),
        'set': set(),
        'dict': dict(),
        'md': multidict.MultiDict(),
    })
