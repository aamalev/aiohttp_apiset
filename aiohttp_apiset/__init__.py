from aiohttp import web

from . import ui
from .config.app import APP_CONFIG_KEY, Config


try:
    from .version import __version__
except ImportError:
    __version__ = 'dev'


__all__ = ['APP_CONFIG_KEY', 'Config', '__version__', 'setup']


def setup(config: Config, app: web.Application, app_key: str = APP_CONFIG_KEY):
    config.setup(app, app_key)
    handler = ui.Handler(config)
    handler.setup(app.router)
