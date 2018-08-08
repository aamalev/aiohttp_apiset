import warnings
from collections import Mapping

from aiohttp import hdrs, web

from . import ui
from .loader import FileLoader
from .operations import get_docstring_swagger
from .route import route_factory, SwaggerRoute
from .. import dispatcher, utils
from ..middlewares import JsonEncoder


class SchemaSerializer(JsonEncoder):
    converters = [
        (0, Mapping, dict),
    ]


class SwaggerRouter(dispatcher.TreeUrlDispatcher):
    """ SwaggerRouter is designed to load swagger specifications

    :param path: path to specification
    :param search_dirs: directory for search files of specification
    :param swagger_ui: if True then swagger-ui will be available
        at the url `basePath`/apidoc/index.html
    :param encoding: default encoding of specification, if None apply UTF-8
    :param route_factory: factory for select route class and create route
    :param default_validate: if True and not specify in method then standart
        route_factory selected SwaggerValidationRoute
    """
    INCLUDE = '$include'
    VIEW = '$view'
    HANDLER = '$handler'
    NAME = '$name'
    VALIDATE = '$validate'

    def __init__(self, path: str=None, *,
                 search_dirs=None, swagger_ui='/apidoc/', version_ui=2,
                 route_factory=route_factory,
                 encoding=None, default_validate=True,
                 file_loader=None, spec_url=None):
        super().__init__(route_factory=route_factory)
        self.app = None
        self._encoding = encoding
        self._swagger_data = {}
        self._default_validate = default_validate
        self._spec_url = spec_url

        if file_loader is None:
            cls = FileLoader.class_factory(include=self.INCLUDE)
            file_loader = cls(encoding=encoding)
        for sd in search_dirs or ():
            file_loader.add_search_dir(sd)
        self._file_loader = file_loader

        if isinstance(swagger_ui, str):
            if not swagger_ui.startswith('/'):
                swagger_ui = '/' + swagger_ui
            if not swagger_ui.endswith('/'):
                swagger_ui += '/'
            spec = swagger_ui + 'swagger.yaml'
            self.add_get(
                spec, self._handler_swagger_spec, name='swagger:spec')
            self.add_get(
                swagger_ui, self._handler_swagger_ui, name='swagger:ui')
            self.add_static(
                swagger_ui, ui.STATIC_UI, name='swagger:ui:static')
            ui.get_template()  # warm up
        self._swagger_ui = swagger_ui
        self._version_ui = version_ui

        if path:
            warnings.warn(
                "path param is deprecated and will be removed. "
                "Use router.include(path) instead",
                DeprecationWarning, stacklevel=2)
            self.include(path)

    def _handler_swagger_spec(self, request):
        key = request.query.get('spec')
        if key is None and self._swagger_data:
            key = next(iter(self._swagger_data), '')

        if key in self._swagger_data and 'paths' in self._swagger_data[key]:
            return web.json_response(self._swagger_data[key],
                                     dumps=SchemaSerializer.dumps)

        for k in sorted(self._swagger_data, reverse=True):
            if key.startswith(k):
                spec = self._swagger_data[k].copy()
                break
        else:
            spec = dict(
                swagger='2.0',
            )

        paths = spec.setdefault('paths', {})
        prefix = spec.get('basePath', '').rstrip('/')
        lprefix = len(prefix)
        default_operation = dict(
            tags=['default'],
            responses={'default': {'description': 'ok'}},
        )
        for r in self.routes():
            url = r.url_for().human_repr()

            if key and not url.startswith(key):
                continue
            elif isinstance(r, SwaggerRoute):
                op = r.swagger_operation
                if op is None:
                    d = None
                else:
                    d = dict(op)
            else:
                d = None

            if not d:
                d = get_docstring_swagger(r.handler)

            if not d:
                d = default_operation

            if 'responses' not in d:
                d['responses'] = default_operation['responses']

            if prefix:
                url = url[lprefix:]
            paths.setdefault(url, {})[r.method.lower()] = d
        return web.json_response(spec, dumps=SchemaSerializer.dumps)

    def _handler_swagger_ui(self, request, spec, version):
        """
        ---
        parameters:
          - name: spec
            in: query
            type: string
          - name: version
            in: query
            type: integer
            enum: [2,3]
        """
        version = version or self._version_ui
        if self._spec_url:
            spec_url = self._spec_url
        else:
            spec_url = request.url.with_path(self['swagger:spec'].url())
            proto = request.headers.get(hdrs.X_FORWARDED_PROTO)
            if proto:
                spec_url = spec_url.with_scheme(proto)
            if isinstance(spec, str):
                spec_url = spec_url.with_query(spec=spec)
            elif len(self._swagger_data) == 1:
                for basePath in self._swagger_data:
                    spec_url = spec_url.with_query(spec=basePath)
            else:
                spec_url = spec_url.with_query(spec='/')
            spec_url = spec_url.human_repr()
        return web.Response(
            text=ui.rend_template(spec_url,
                                  prefix=self._swagger_ui,
                                  version=version),
            content_type='text/html')

    def include(self, spec, *,
                basePath=None,
                operationId_mapping=None,
                name=None):
        """ Adds a new specification to a router

        :param spec: path to specification
        :param basePath: override base path specify in specification
        :param operationId_mapping: mapping for handlers
        :param name: name to access original spec
        """

        data = self._file_loader.load(spec)

        if basePath is None:
            basePath = data.get('basePath', '')

        if name is not None:
            d = dict(data)
            d['basePath'] = basePath
            self._swagger_data[name] = d
            # TODO clear d

        swagger_data = {k: v for k, v in data.items() if k != 'paths'}
        swagger_data['basePath'] = basePath

        for url, methods in data.get('paths', {}).items():
            url = basePath + url
            methods = methods.copy()
            location_name = methods.pop(self.NAME, None)
            parameters = methods.pop('parameters', [])
            for method, body in methods.items():
                if method == self.VIEW:
                    view = utils.import_obj(body)
                    view.add_routes(self, prefix=url, encoding=self._encoding)
                    continue
                body = body.copy()
                if parameters:
                    body['parameters'] = parameters + \
                                         body.get('parameters', [])
                handler = body.pop(self.HANDLER, None)
                name = location_name or handler
                if not handler:
                    op_id = body.get('operationId')
                    if op_id and operationId_mapping:
                        handler = operationId_mapping.get(op_id)
                        if handler:
                            name = location_name or op_id
                if handler:
                    validate = body.pop(self.VALIDATE, self._default_validate)
                    self.add_route(
                        method.upper(), utils.url_normolize(url),
                        handler=handler,
                        name=name,
                        swagger_data=body,
                        validate=validate,
                    )
        self._swagger_data[basePath] = swagger_data

        for route in self.routes():
            if isinstance(route, SwaggerRoute) and not route.is_built:
                route.build_swagger_data(self._file_loader)

    def add_search_dir(self, path):
        """Add directory for search specification files
        """
        self._file_loader.add_search_dir(path)

    def add_route(self, method, path, handler,
                  *, name=None, expect_handler=None,
                  swagger_data=None,
                  validate=None):
        """ Returns route

        :param method: as well as in aiohttp
        :param path: as well as in aiohttp
        :param handler: as well as in aiohttp
            and also must be str `mymodule.handler`
        :param name: as well as in aiohttp
        :param expect_handler: as well as in aiohttp
        :param swagger_data: data
            http://swagger.io/specification/#operationObject
        :param validate: bool param for validate in SwaggerValidationRoute
        :param build: bool param for build extractor and validator
        :return: route for handler
        """
        if name is None or name in self._named_resources:
            name = ''

        if validate is None:
            validate = self._default_validate

        route = super().add_route(
            method, path, handler, name=name,
            expect_handler=expect_handler,
            swagger_data=swagger_data,
            validate=validate,
        )
        return route

    def setup(self, app: web.Application):
        """ Installation routes to app.router

        :param app: instance of aiohttp.web.Application
        """
        if self.app is app:
            raise ValueError('The router is already configured '
                             'for this application')
        self.app = app
        routes = sorted(
            ((r.name, (r, r.url_for().human_repr())) for r in self.routes()),
            key=utils.sort_key)
        exists = set()
        for name, (route, path) in routes:
            if name and name not in exists:
                exists.add(name)
            else:
                name = None
            app.router.add_route(
                route.method, path,
                route.handler, name=name)

    def freeze(self):
        for r in self.routes():
            if isinstance(r, SwaggerRoute):
                r.build_swagger_data(self._file_loader)
        super().freeze()
