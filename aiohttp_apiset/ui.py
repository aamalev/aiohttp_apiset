from functools import lru_cache
from pathlib import Path
from typing import Optional

from aiohttp import hdrs, web

from .config.app import Config, UIType
from .decorators import operation
from .openapi.loader.base import ExportFormat
from .schema import Parameter


ROUTE_SPEC_DEFAULT = 'aiohttp_apiset:spec'
ROUTE_SPEC_YAML = 'aiohttp_apiset:spec:yaml'
ROUTE_SPEC_JSON = 'aiohttp_apiset:spec:json'
ROUTE_SPEC_ANY = 'aiohttp_apiset:spec:any'
ROUTE_UI = 'aiohttp_apiset:ui'
ROUTE_UI_STATIC = 'aiohttp_apiset:ui:static'

DIR_ROOT = Path(__file__).parent
DIR_STATIC = DIR_ROOT / 'static'
DIR_STATIC_UI = {
    UIType.swagger_ui: DIR_STATIC / 'swagger-ui',
    UIType.redoc: DIR_STATIC / 'redoc'

}
DIR_TEMPLATES = DIR_ROOT / 'templates'
TEMPLATES_SWAGGER_UI = {
    2: DIR_TEMPLATES / 'swagger-ui' / '2' / 'index.html',
    3: DIR_TEMPLATES / 'swagger-ui' / '3' / 'index.html',
    4: DIR_TEMPLATES / 'swagger-ui' / '4' / 'index.html',
}
TEMPLATE_REDOC = DIR_TEMPLATES / 'redoc' / 'index.html'


@lru_cache()
def _get_template(ui_type: UIType, version: int) -> str:
    if ui_type == UIType.swagger_ui:
        with TEMPLATES_SWAGGER_UI[version].open() as f:
            return f.read()
    else:
        assert ui_type == UIType.redoc
        with TEMPLATE_REDOC.open() as f:
            return f.read()


class Handler:
    def __init__(self, config: Config):
        self.config = config

    def setup(self, router: web.UrlDispatcher):
        get_spec_handler = operation(
            Parameter.path('filename').set_schema(type_='string')
        )(self.get_spec)

        get_ui_handler = operation(
            Parameter.query('version').set_schema(
                type_='integer',
                enum=[2, 3, 4]
            )
        )(self.get_ui)

        path = self.config.ui_path
        router.add_get(path + 'swagger.yml', get_spec_handler, name=ROUTE_SPEC_DEFAULT)
        router.add_get(path + 'swagger.yaml', get_spec_handler, name=ROUTE_SPEC_YAML)
        router.add_get(path + 'swagger.json', get_spec_handler, name=ROUTE_SPEC_JSON)
        router.add_get(path + r'{filename:.*\.(json|yaml|yml)}', get_spec_handler, name=ROUTE_SPEC_ANY)
        router.add_get(path, get_ui_handler, name=ROUTE_UI)
        router.add_static(path, DIR_STATIC_UI[self.config.ui_type], name=ROUTE_UI_STATIC)
        _get_template(self.config.ui_type, self.config.ui_version)  # warm up

    def _get_specification_url(self, request: web.Request) -> str:
        default_url = self.config.ui_spec_url
        if default_url is not None:
            return default_url

        path = request.app.router[ROUTE_SPEC_DEFAULT].url_for()
        url = request.url.with_path(str(path))
        proto = request.headers.get(hdrs.X_FORWARDED_PROTO)
        if proto:
            url = url.with_scheme(proto)
        return url.human_repr()

    def _render_ui_template(self, spec_url: str, ui_version: Optional[int] = None) -> str:
        if ui_version is None:
            ui_version = self.config.ui_version
        template = _get_template(self.config.ui_type, ui_version)
        static_prefix = self.config.ui_path
        if self.config.ui_type == UIType.swagger_ui:
            static_prefix += str(ui_version) + '/'
        template = template.replace('{{url}}', spec_url)
        return template.replace('{{static_prefix}}', static_prefix)

    async def get_ui(self, request: web.Request, version: Optional[int]) -> web.Response:
        spec_url = self._get_specification_url(request)
        content = self._render_ui_template(spec_url=spec_url, ui_version=version)
        return web.Response(text=content, content_type='text/html')

    async def get_spec(self, request: web.Request, filename: Optional[str]) -> web.Response:
        raw_export_format = request.path.split('.')[-1]
        if raw_export_format == 'yml':
            raw_export_format = 'yaml'
        export_format = ExportFormat(raw_export_format)
        if export_format == ExportFormat.json:
            content_type = 'application/json'
        elif export_format == ExportFormat.yaml:
            content_type = 'application/x-yaml'
        else:
            raise NotImplementedError()  # pragma: no cover
        try:
            data = self.config.loader.dump(filename, export_format)
        except FileNotFoundError:
            raise web.HTTPNotFound(reason='No such file: {}'.format(filename))
        return web.Response(text=data, content_type=content_type)
