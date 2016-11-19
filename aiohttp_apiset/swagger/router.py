import importlib
import os
from urllib.parse import urljoin

import yaml
from aiohttp import web, multidict

from .. import dispatcher, utils
from . import ui
from .operations import get_docstring_swagger
from .route import route_factory, SwaggerRoute


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

    def __init__(self, path: str=None, *, search_dirs=None, swagger_ui=True,
                 encoding=None, route_factory=route_factory,
                 default_validate=False):
        super().__init__(route_factory=route_factory)
        self.app = None
        self._routes = multidict.MultiDict()
        self._encoding = encoding
        self._search_dirs = search_dirs or []
        self._swagger_data = {}
        self._swagger_yaml = {}
        self._swagger_ui = swagger_ui
        self._default_validate = default_validate
        if path:
            self.include(path)

    def _handler_swagger_spec(self, request):
        key = request.raw_path
        return web.Response(text=self._swagger_yaml[key])

    def _handler_swagger_ui(self, request):
        url = urljoin(request.raw_path, 'swagger.yaml')
        return web.Response(text=ui.rend_template(url),
                            content_type='text/html')

    def include(self, spec, *, basePath=None, operationId_mapping=None):
        """ Adds a new specification to a router

        :param spec: path to specification
        :param basePath: override base path specify in specification
        """
        path = utils.find_file(spec, self._search_dirs)
        if not self._search_dirs:
            d = os.path.dirname(path)
            self._search_dirs.append(d)
        data = self._include(file_path=path, override_basePath=basePath,
                             operationId_mapping=operationId_mapping)
        basePath = data.get('basePath', '')
        self._swagger_data[basePath] = data

        if self._swagger_ui:
            base_ui = basePath + '/apidoc/'
            spec = base_ui + 'swagger.yaml'
            if spec not in self._swagger_yaml:
                index = base_ui + 'index.html'
                self.add_route('GET', spec, self._handler_swagger_spec)
                self.add_route('GET', index, self._handler_swagger_ui)
                self.add_route('GET', base_ui, self._handler_swagger_ui)
                self.add_static(base_ui, ui.STATIC_UI)
                ui.get_template()  # warm up
            self._swagger_yaml[spec] = yaml.dump(data)

        for url in self._routes:
            for route, path in self._routes.getall(url):
                if isinstance(route, SwaggerRoute) and not route.is_built:
                    route.build_swagger_data(data)

    def add_search_dir(self, path):
        """Add directory for search specification files
        """
        self._search_dirs.append(path)

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
        :return: route for handler
        """
        if name in self._routes:
            name = ''
        route = super().add_route(
            method, path, handler, name=name,
            expect_handler=expect_handler,
            swagger_data=swagger_data,
            validate=validate,
        )
        self._routes.add(name, (route, path))
        return route

    def setup(self, app: web.Application):
        """ Installation routes to app.router

        :param app: instance of aiohttp.web.Application
        """
        self.app = app
        routes = sorted(self._routes.items(), key=utils.sort_key)
        for name, (route, path) in routes:
            name = name or None
            app.router.add_route(
                route.method, path,
                route.handler, name=name)

        if self._swagger_ui:
            def generator(data):
                def view(request):
                    return web.Response(text=data)
                return view

            for url, body in self._swagger_yaml.items():
                app.router.add_route(
                    'GET',
                    utils.url_normolize(url),
                    generator(body))

    def import_view(self, p: str):
        p, c = p.rsplit('.', 1)
        package = importlib.import_module(p)
        return getattr(package, c)

    def _include_item(self, item, base_dir, prefix, url,
                      swagger_prefix, swagger_data,
                      definitions, paths, operationId_mapping=None):
        base_url = prefix + url

        if isinstance(item, list):
            for i in item:
                self._include_item(
                    i, base_dir, prefix, url,
                    swagger_prefix, swagger_data,
                    definitions, paths)

        elif isinstance(item, str):
            raise NotImplementedError()

        elif self.VIEW in item:
            view = self.import_view(item.pop(self.VIEW))
            view.add_routes(
                self, prefix=base_url, encoding=self._encoding)
            s = view.get_sub_swagger(['paths'], default={})
            b = view.get_sub_swagger('basePath', default='')
            for u, i in s.items():
                u = swagger_prefix + url + b + u
                u = utils.remove_patterns(u)
                paths[u] = i
            definitions.update(
                view.get_sub_swagger(['definitions'], default={}))

        elif self.INCLUDE in item:
            f = utils.find_file(
                file_path=item[self.INCLUDE],
                search_dirs=self._search_dirs,
                base_dir=base_dir)
            self._include(
                f,
                prefix=prefix + url,
                swagger_prefix=swagger_prefix + url,
                swagger_data=swagger_data,
                operationId_mapping=operationId_mapping,
            )

        else:
            paths[utils.remove_patterns(swagger_prefix + url)] = item
            location_name = item.pop(self.NAME, None)
            base_url = utils.url_normolize(base_url)
            replace = {}
            for method, body in item.items():
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
                    route = self.add_route(
                        method.upper(), base_url, handler=handler,
                        name=name,
                        swagger_data=body,
                        validate=validate,
                    )
                    if isinstance(route, SwaggerRoute):
                        replace[method] = route._swagger_data
            item.update(replace)

    def _include(self, file_path, prefix=None, swagger_prefix=None,
                 swagger_data=None, override_basePath=None,
                 operationId_mapping=None):
        base_dir = os.path.dirname(file_path)

        with open(file_path, encoding=self._encoding) as f:
            data = yaml.load(f)

        if prefix is None:
            prefix = ''

        if override_basePath is None:
            basePath = data.get('basePath', '')
        else:
            basePath = override_basePath

        if swagger_prefix is None:
            swagger_prefix = ''
        else:
            swagger_prefix += basePath

        prefix += basePath
        base_paths = data['paths']

        if swagger_data is None:
            if basePath in self._swagger_data:
                swagger_data = self._swagger_data[basePath]
            else:
                swagger_data = data.copy()
                swagger_data['paths'] = {}
                swagger_data['basePath'] = basePath
                swagger_data['definitions'] = {}
        paths = swagger_data['paths']
        definitions = swagger_data['definitions']
        definitions.update(data.get('definitions', {}))

        for url in base_paths:
            item = base_paths[url]
            self._include_item(
                item, base_dir, prefix, url,
                swagger_prefix, swagger_data,
                definitions, paths,
                operationId_mapping=operationId_mapping)

        return swagger_data
