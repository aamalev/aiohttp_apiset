import importlib
import os
from urllib.parse import urljoin

import yaml
from aiohttp import web, multidict

from . import utils, views, dispatcher
from .swagger.route import route_factory, SwaggerRoute
from .swagger import ui


class SwaggerRouter(dispatcher.TreeUrlDispatcher):
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

    def include(self, spec, *, basePath=None):
        path = utils.find_file(spec, self._search_dirs)
        if not self._search_dirs:
            d = os.path.dirname(path)
            self._search_dirs.append(d)
        data = self._include(file_path=path, override_basePath=basePath)
        basePath = data.get('basePath', '')
        self._swagger_data[basePath] = data

        if self._swagger_ui:
            base_ui = basePath + '/apidoc/'
            spec = base_ui + 'swagger.yaml'
            index = base_ui + 'index.html'
            self._swagger_yaml[spec] = yaml.dump(data)
            self.add_route('GET', spec, self._handler_swagger_spec)
            self.add_route('GET', index, self._handler_swagger_ui)
            self.add_static(base_ui, ui.STATIC_UI)
            ui.get_template()  # warm up

        for url in self._routes:
            for route, path in self._routes.getall(url):
                if isinstance(route, SwaggerRoute):
                    route.build_swagger_data(data)

    def add_search_dir(self, path):
        self._search_dirs.append(path)

    def add_route(self, method, path, handler,
                  *, name=None, expect_handler=None,
                  swagger_data=None,
                  validate=None):
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
                      definitions, paths):
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
                swagger_data=swagger_data)

        else:
            paths[utils.remove_patterns(swagger_prefix + url)] = item
            name = item.pop(self.NAME, None)
            base_url = utils.url_normolize(base_url)
            for method, body in item.items():
                handler_str = body.pop(self.HANDLER, None)
                if handler_str:
                    validate = body.pop(self.VALIDATE, self._default_validate)
                    self.add_route(
                        method.upper(), base_url, handler=handler_str,
                        name=name or handler_str,
                        swagger_data=body,
                        validate=validate,
                    )

    def _include(self, file_path, prefix=None, swagger_prefix=None,
                 swagger_data=None, override_basePath=''):
        base_dir = os.path.dirname(file_path)

        with open(file_path, encoding=self._encoding) as f:
            data = yaml.load(f)

        if prefix is None:
            prefix = ''

        if swagger_prefix is None:
            swagger_prefix = ''
        else:
            swagger_prefix += data.get('basePath', override_basePath)

        prefix += data.get('basePath', override_basePath)
        base_paths = data['paths']

        if swagger_data is None:
            swagger_data = data.copy()
            swagger_data['paths'] = {}
            swagger_data['definitions'] = {}
        paths = swagger_data['paths']
        definitions = swagger_data['definitions']
        definitions.update(data.get('definitions', {}))

        for url in base_paths:
            item = base_paths[url]
            self._include_item(
                item, base_dir, prefix, url,
                swagger_prefix, swagger_data,
                definitions, paths)

        return swagger_data


class APIRouter(views.BaseApiSet):
    def __init__(self, prefix_url=None):
        self.views = []
        self.prefix_url = prefix_url

    def append_routes_from(self, view):
        self.views.append(view)

    def append_routes_to(self, app, prefix=None):
        prefix = prefix or self.prefix_url
        for view in self.views:
            view.append_routes_to(app, prefix)
