import importlib
import os

import yaml
from aiohttp import web

from . import utils, views


class SwaggerRouter:
    def __init__(self, path: str, *, search_dirs=None, swagger=True):
        self.app = None
        self.routes = []
        search_dirs = search_dirs or ()
        self._swagger_root = utils.find_file(path, search_dirs)
        self._search_dirs = search_dirs or [
            os.path.dirname(self._swagger_root)]
        self._swagger_data = self.include(file_path=self._swagger_root)
        self._swagger_yaml = yaml.dump(self._swagger_data)
        self._swagger = swagger

    def setup(self, app: web.Application):
        self.app = app
        for url, view, name in self.routes:
            app.router.add_route('*', url, view)

        if self._swagger:
            url = self._swagger_data.get('basePath', '') + '/swagger.yaml'
            app.router.add_route('GET', url, self.swagger_view)

    def swagger_view(self, request):
        return web.Response(text=self._swagger_yaml)

    def import_view(self, p: str):
        p, c = p.rsplit('.', 1)
        package = importlib.import_module(p)
        return getattr(package, c)

    def connect_view(self, data, base_url, url, klass):
        view = klass(self.app, prefix=url)
        for d in view.get_routes(base_url=url):
            self.app.router.add_route(
                d['method'], base_url + d['path'],
                d['handler'], name=d['name'])
            path = data['paths'].setdefault(d['path'], {})
            path.update(d['swagger_path'])

    def include(self, file_path, prefix=None, paths=None):
        base_dir = os.path.dirname(file_path)
        with open(file_path) as f:
            data = yaml.load(f)
        if prefix:
            prefix = data.get('basePath', '') + prefix
        else:
            prefix = ''
        base_paths = data['paths']
        if paths is None:
            data['paths'] = paths = {}
        for url in base_paths:
            item = base_paths[url]
            base_url = prefix + url
            if '$view' in item:
                view = self.import_view(item.pop('$view'))
                view.add_routes(self.routes, prefix=base_url)
                paths[base_url] = view.get_swagger_paths()
            elif '$include' in item:
                f = utils.find_file(
                    file_path=item['$include'],
                    search_dirs=self._search_dirs,
                    base_dir=base_dir)
                self.include(f, prefix=base_url, paths=paths)
            else:
                paths[base_url] = item
        return data


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
