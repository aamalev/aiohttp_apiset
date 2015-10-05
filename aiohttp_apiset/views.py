import asyncio
import json
import os
import sys

from aiohttp import web
from aiohttp.web_urldispatcher import PlainRoute
import yaml


def swagger_yaml(file_path, *, executor=None, loop=None):
    loop = loop or asyncio.get_event_loop()

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


class ApiSet:
    prefix = '/api/'
    version = 1
    docs = '/docs/'
    api_docs = 'api-docs'
    spacename = ''
    swagger_file = 'swagger.yaml'
    default_response = 'json'
    actions = (
        ('create', 'POST', ''),
        ('post', 'POST', ''),
        ('list', 'GET', ''),
        ('get', 'GET', ''),
        ('retrieve', 'GET', '{id}/'),
    )

    @asyncio.coroutine
    def swagger(self, request):
        module_path = sys.modules[self.__module__].__file__
        swagger_file = os.path.join(
            os.path.dirname(module_path), self.swagger_file)
        return (yield from swagger_yaml(swagger_file)(request))

    @classmethod
    def append_routes_to(cls, router):
        self = cls()
        url = self.prefix + str(self.version) + '/' + self.spacename + '/'
        router.register_route(PlainRoute(
            'GET', self.swagger, ':'.join((self.spacename, 'swagger')),
            self.prefix + str(self.version) + self.docs + self.api_docs + url))

        for action_name, method, postfix_url in self.actions:
            action = getattr(self, action_name, None)
            if action:
                router.register_route(
                    PlainRoute(method, action,
                               ':'.join((self.spacename, action_name)),
                               url + postfix_url))

    def response(self, data, **kwargs):
        if isinstance(data, dict):
            data = data.copy()
        else:
            data = {'data_text': str(data)}
        data.update(kwargs)
        return getattr(
            self,
            'response_' + self.default_response,
        )(data)

    @classmethod
    def response_json(cls, data):
        data = json.dumps(
            data,
            indent=3,
            ensure_ascii=False,
        )
        return web.Response(
            body=data.encode(),
            content_type='application/json')
