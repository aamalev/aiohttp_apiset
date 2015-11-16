import yaml
from aiohttp.web import Application

from .views import BaseApiSet


class SwaggerRouter(BaseApiSet):
    def __init__(self, app: Application):
        self.app = app

    def import_view(self, p: str):
        p, c = p.rsplit('.', 1)
        package = __import__(p)
        return getattr(package, c)

    def connect_view(self, data, base_url, url, klass):
        view = klass(self.app, prefix=url)
        for d in view.get_routes(base_url=url):
            self.app.router.add_route(
                d['method'], base_url + d['path'],
                d['handler'], name=d['name'])
            path = data['paths'].setdefault(d['path'], {})
            path.update(d['swagger_path'])

    def load_routes_from_swagger(self, file_path):
        with open(file_path) as f:
            data = yaml.load(f)
        base_url = data['basePath']
        for url in data['paths'].copy():
            item = data['paths'][url]
            if '$view' in item:
                klass = self.import_view(item.pop('$view'))
                self.connect_view(data, base_url, url, klass)
            elif '$include' in item:
                pass
        return data

    @classmethod
    def append_routes_to(cls, app: Application, prefix=None):
        pass


class APIRouter(BaseApiSet):
    def __init__(self, prefix_url=None):
        self.views = []
        self.prefix_url = prefix_url

    def append_routes_from(self, view):
        self.views.append(view)

    def append_routes_to(self, app, prefix=None):
        prefix = prefix or self.prefix_url
        for view in self.views:
            view.append_routes_to(app, prefix)
