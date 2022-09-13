import os
from pathlib import Path

import pytest
import yaml
from aiohttp import web

from aiohttp_apiset.config.app import Config, UIType
from aiohttp_apiset.openapi.loader.v3_1 import Loader
from aiohttp_apiset.ui import (
    ROUTE_SPEC_ANY,
    ROUTE_SPEC_DEFAULT,
    ROUTE_SPEC_JSON,
    ROUTE_SPEC_YAML,
    ROUTE_UI,
    Handler,
)


DATA_ROOT = Path(__file__).parent / 'data' / 'ui'


@pytest.mark.skipif(os.environ.get('FAKE_UI') == 'yes', reason='UI is not downloaded')
@pytest.mark.parametrize('ui_type', [UIType.swagger_ui, UIType.redoc])
@pytest.mark.parametrize('ui_spec_url', ['/custom-spec-url', None])
async def test_handler(aiohttp_client, ui_type, ui_spec_url):
    loader = Loader()
    loader.add_directory(DATA_ROOT)
    loader.load('v3_1.yaml')
    config = Config(loader, ui_spec_url=ui_spec_url, ui_type=ui_type, ui_version=3)
    handler = Handler(config)
    app = web.Application()
    handler.setup(app.router)
    client = await aiohttp_client(app)
    url = app.router[ROUTE_UI].url_for()

    rep = await client.get(url)
    assert rep.status == 200, await rep.text()
    assert rep.headers['Content-Type'] == 'text/html; charset=utf-8'

    rep = await client.get(url, headers={'X-Forwarded-Proto': 'https'})
    assert rep.status == 200, await rep.text()
    assert rep.headers['Content-Type'] == 'text/html; charset=utf-8'
    data = await rep.text()
    if ui_spec_url is None:
        assert 'apidoc/swagger.yml' in data
    else:
        assert ui_spec_url in data

    for route_name in [ROUTE_SPEC_YAML, ROUTE_SPEC_DEFAULT]:
        url = app.router[route_name].url_for()
        rep = await client.get(url)
        assert rep.status == 200, await rep.text()
        raw_data = await rep.read()
        data = yaml.load(raw_data, yaml.Loader)
        assert data['openapi'] == '3.1.0'

    url = app.router[ROUTE_SPEC_JSON].url_for()
    rep = await client.get(url)
    assert rep.status == 200, await rep.text()
    data = await rep.json()
    assert data['openapi'] == '3.1.0'

    url = app.router[ROUTE_SPEC_ANY].url_for(filename='notfound.yaml')
    rep = await client.get(url)
    assert rep.status == 404, await rep.text()
