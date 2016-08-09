import importlib
import os

import yaml
from aiohttp import web, multidict

from . import utils, views


class SwaggerRouter:
    def __init__(self, path: str=None, *, search_dirs=None, swagger=True,
                 encoding=None):
        self.app = None
        self._routes = multidict.MultiDict()
        self._encoding = encoding
        self._singleton_cbv = {}
        self._search_dirs = search_dirs or []
        self._swagger_data = {}
        self._swagger_yaml = {}
        self._swagger = swagger
        self.include(path)

    def include(self, spec, *, basePath=None):
        path = utils.find_file(spec, self._search_dirs)
        if not self._search_dirs:
            d = os.path.dirname(path)
            self._search_dirs.append(d)
        if self._swagger:
            data = self._include(file_path=path)
            if basePath is None:
                basePath = data.get('basePath', '')
            url = basePath + '/swagger.yaml'
            self._swagger_data[url] = data
            self._swagger_yaml[url] = yaml.dump(data)

    def add_search_dir(self, path):
        self._search_dirs.append(path)

    def add_route(self, method, path, handler, *, name=None):
        if name in self._routes:
            name = ''
        self._routes.add(name, utils.Route(method, path, handler))

    def __getitem__(self, item):
        return self._routes.get(item)

    def setup(self, app: web.Application):
        self.app = app
        routes = sorted(self._routes.items(), key=utils.sort_key)
        for name, (method, url, handler) in routes:
            name = name or None
            app.router.add_route(method, url, handler, name=name)

        if self._swagger:
            def generator(data):
                async def view(request):
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

    def import_handler(self, path: str):
        p = path.rsplit('.', 2)
        if len(p) == 3:
            p, v, h = p
            if v == v.lower():
                p = '.'.join((p, v))
                v = None
        elif len(p) == 2:
            p, h = p
            v = None
        else:
            raise ValueError('.'.join(p))

        package = importlib.import_module(p)

        if not v:
            return getattr(package, h)

        key = '.'.join((p, v))
        if key in self._singleton_cbv:
            v = self._singleton_cbv[key]
        else:
            View = getattr(package, v)
            v = View()
            self._singleton_cbv[key] = v
        return getattr(v, h)

    def connect_view(self, data, base_url, url, klass):
        view = klass(self.app, prefix=url)
        for d in view.get_routes(base_url=url):
            self.app.router.add_route(
                d['method'], base_url + d['path'],
                d['handler'], name=d['name'])
            path = data['paths'].setdefault(d['path'], {})
            path.update(d['swagger_path'])

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

        elif '$view' in item:
            view = self.import_view(item.pop('$view'))
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

        elif '$include' in item:
            f = utils.find_file(
                file_path=item['$include'],
                search_dirs=self._search_dirs,
                base_dir=base_dir)
            self._include(
                f,
                prefix=prefix + url,
                swagger_prefix=swagger_prefix + url,
                swagger_data=swagger_data)

        else:
            paths[utils.remove_patterns(swagger_prefix + url)] = item
            base_url = utils.url_normolize(base_url)
            for method, body in item.items():
                handler_str = body.pop('$handler', None)
                if handler_str:
                    handler = self.import_handler(handler_str)
                    self.add_route(
                        method.upper(), base_url, handler,
                        name=handler_str)

    def _include(self, file_path, prefix=None, swagger_prefix=None,
                 swagger_data=None):
        base_dir = os.path.dirname(file_path)

        with open(file_path, encoding=self._encoding) as f:
            data = yaml.load(f)

        if prefix is None:
            prefix = ''

        if swagger_prefix is None:
            swagger_prefix = ''
        else:
            swagger_prefix += data.get('basePath', '')

        prefix += data.get('basePath', '')
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
