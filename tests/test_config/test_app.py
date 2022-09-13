from pathlib import Path

import pytest
from aiohttp import web

from aiohttp_apiset.config.app import APP_CONFIG_KEY, Config
from aiohttp_apiset.openapi.loader.v2_0 import Loader as LoaderV2
from aiohttp_apiset.openapi.loader.v3_1 import Loader as LoaderV3


DATA_ROOT = Path(__file__).parent.parent / 'data' / 'config'


def test_create_config():
    loader = LoaderV3()
    config = Config(loader, ui_path='docs')
    assert config.loader is loader
    assert config.ui_path == '/docs/'
    with pytest.raises(ValueError, match='Unexpected UI version 0'):
        config = Config(loader, ui_version=0)


@pytest.mark.parametrize('version,loader_cls', [('v2_0', LoaderV2), ('v3_1', LoaderV3)])
async def test_setup_routes(aiohttp_client, version, loader_cls):
    loader = loader_cls()
    loader.add_directory(DATA_ROOT)
    loader.load(version + '.yaml')
    config = Config(loader)
    config.add_operation('GET', '/add', create_add_handler(version))

    with pytest.raises(ValueError, match='A handler has no doc comment'):
        config.add_operation('GET', '/test', handler_without_doc_comment)
    with pytest.raises(ValueError, match='A handler doc comment has no operation data'):
        config.add_operation('GET', '/test', handler_without_spec)

    assert config.route_base_path == '/'

    app = web.Application()
    config.setup(app)
    assert app[APP_CONFIG_KEY] is config

    client = await aiohttp_client(app)

    rep = await client.get('/greet/user')
    assert rep.status == 200, await rep.text()
    data = await rep.json()
    assert data['msg'] == 'Hello, user!'

    rep = await client.get('/add', params={'a': '2', 'b': '2'})
    assert rep.status == 200, await rep.text()
    data = await rep.json()
    assert data['value'] == 4


def create_add_handler(version):
    if version == 'v2_0':
        comment = """
        ---
        parameters:
          - name: a
            in: query
            type: integer
            required: true
          - name: b
            in: query
            type: integer
            required: true
        responses:
          '200':
            description: OK
        """
    elif version == 'v3_1':
        comment = """
        ---
        parameters:
          - name: a
            in: query
            schema:
                type: integer
            required: true
          - name: b
            in: query
            schema:
                type: integer
            required: true
        """
    else:
        raise NotImplementedError()  # pragma: no cover

    async def add_handler(a, b):
        return web.json_response({'value': a + b})

    add_handler.__doc__ = comment

    return add_handler


async def greet(user):
    return web.json_response({'msg': 'Hello, {}!'.format(user)})


async def handler_without_doc_comment():
    pass  # pragma: no cover


async def handler_without_spec():
    """
    """


async def goodbye(user):
    """
    ---
    parameters: [{name: user, in: path, type: string, required: true}]
    responses:
        200:
            description: OK
    """
    return web.json_response({'msg': 'Goodbye, {}!'.format(user)})


async def test_add_operation_for_str_handler(aiohttp_client):
    loader = LoaderV2()
    loader.add_directory(DATA_ROOT)
    loader.load('v2_0.yaml')
    config = Config(loader)
    config.add_operation('GET', '/goodbye/{user}', 'tests.test_config.test_app.goodbye')
    app = web.Application()
    config.setup(app)
    client = await aiohttp_client(app)

    rep = await client.get('/goodbye/user')
    assert rep.status == 200, await rep.text()
    data = await rep.json()
    assert data['msg'] == 'Goodbye, user!'
