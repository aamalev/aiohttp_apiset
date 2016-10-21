import asyncio
import functools
import inspect
import json
import os
import sys

from aiohttp import web, abc
from aiohttp.web import Application
import yaml

from .swagger.loader import SwaggerLoaderMixin
from . import utils

PY_35 = sys.version_info >= (3, 5)


class BaseApiSet:
    @classmethod
    def append_routes_to(cls, app: Application, prefix=None):
        raise NotImplementedError()


def swagger_yaml(file_path, *, executor=None, loop=None):
    if loop is None:
        loop = asyncio.get_event_loop()

    def response(request):
        with open(file_path) as f:
            data = yaml.load(f)
            return ApiSet.response_json(data)

    @asyncio.coroutine
    def aresponse(request):
        return (
            yield from loop.run_in_executor(
                executor, response, request))

    return aresponse


class ApiSet(BaseApiSet, SwaggerLoaderMixin):
    namespace = NotImplemented
    root_dir = '/'
    swagger_ref = None
    methods = {
        '': (
            ('options', 'OPTIONS'),
            ('create', 'POST'),
            ('post', 'POST'),
            ('put', 'PUT'),
            ('patch', 'PATCH'),
            ('list', 'GET'),
            ('get', 'GET'),
        ),
        '/{id}': (
            ('options', 'OPTIONS'),
            ('retrieve', 'GET'),
            ('save', 'POST'),
            ('delete', 'DELETE'),
        ),
    }
    _prefix = None

    dumps = functools.partial(
        json.dumps,
        indent=3,
        ensure_ascii=False,
    )

    @classmethod
    def factory(cls, prefix, encoding=None):
        assert prefix in cls.methods

        class View(cls):
            _prefix = prefix
            _encoding = encoding
            _methods = dict((y, x) for x, y in cls.methods[prefix])

        return View

    @classmethod
    def add_routes(cls, router, prefix, encoding=None):
        basePath = cls.get_sub_swagger('basePath', default='')
        prefix += basePath
        for postfix in cls.methods:
            view = cls.factory(postfix, encoding=encoding)
            u = utils.url_normolize(prefix + postfix)
            name = utils.to_name(cls.namespace + postfix)
            router.add_route('*', u, view, name=name)

    @classmethod
    def get_swagger_paths(cls):
        return cls.get_sub_swagger('paths')

    @property
    def loop(self):
        return self.app.loop

    @asyncio.coroutine
    def options(self, request):
        return web.Response(body=b'')

    @asyncio.coroutine
    def data(self, request) -> dict:
        if 'json' in request.content_type:
            data = yield from request.json()
        else:
            data = yield from request.post()
        return data

    @asyncio.coroutine
    def swagger(self, request):
        module_path = sys.modules[self.__module__].__file__
        swagger_file = os.path.join(
            os.path.dirname(module_path), self.swagger_file)
        return (yield from swagger_yaml(swagger_file)(request))

    def add_swagger_route(self, router, prefix=None, namespace=None):
        router.add_route(
            'GET',
            prefix + str(self.version) + self.docs + self.namespace,
            self.swagger,
            name=':'.join((namespace, 'swagger')),
        )

    def add_action_routes(self, router, prefix=None, namespace=None):
        url = prefix + str(self.version) + '/' + self.namespace + '/'
        for action_name, method, postfix_url in self.actions:
            action = getattr(self, action_name, None)
            if action:
                if method == 'OPTIONS':
                    name = None
                else:
                    name = ':'.join((namespace, action_name))
                router.add_route(method, url + postfix_url, action, name=name)

    def get_routes(self, base_url, namespace=None):
        if not namespace:
            namespace = namespace or self.namespace
            namespace = namespace.replace('/', '.')

        for action_name, method, postfix_url in self.actions:
            action = getattr(self, action_name, None)
            if action:
                yield {
                    'method': method,
                    'path': base_url + postfix_url,
                    'handler': action,
                    'name': ':'.join((namespace, action_name)),
                    'swagger_path': self.swagger_path,
                }

    @classmethod
    def append_routes_to(cls, app: Application, prefix=None):
        self = cls(app)
        prefix = prefix or self._prefix
        namespace = self.namespace.replace('/', '.')
        namespace = namespace.replace('{', '')
        namespace = namespace.replace('}', '')
        self.add_swagger_route(app.router, prefix, namespace)
        self.add_action_routes(app.router, prefix, namespace)

    @classmethod
    def response(cls, data=None, **kwargs):
        response = getattr(cls, 'response_' + cls.default_response)
        if isinstance(data, dict):
            data = data.copy()
        elif not data:
            data = {}
        elif isinstance(data, (map, list, set, tuple)):
            return response(data, **kwargs)
        else:
            data = {'data_text': str(data)}
        data.update(kwargs)
        return response(data, **kwargs)

    @classmethod
    def response_json(cls, data, **kwargs):
        return web.json_response(
            data,
            content_type='application/json; charset=utf-8',
            status=kwargs.get('status', 200),
            dumps=cls.dumps,
        )
