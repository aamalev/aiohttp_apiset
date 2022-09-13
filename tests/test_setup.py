from pathlib import Path

from aiohttp import web

from aiohttp_apiset import Config
from aiohttp_apiset import setup as setup_api
from aiohttp_apiset.openapi.loader.v3_1 import Loader


DATA_ROOT = Path(__file__).parent / 'data' / 'config'


def test_setup():
    loader = Loader()
    loader.add_directory(DATA_ROOT)
    loader.load('v3_1.yaml')
    config = Config(loader)
    app = web.Application()
    setup_api(config, app, app_key='openapi')
    assert app['openapi'] is config
