import asyncio
import inspect

from aiohttp import web

from ..dispatcher import Route
from .validate import types_mapping, validate


class SwaggerValidationRoute(Route):

    def __init__(self, method, handler, resource, *,
                 expect_handler=None, location=None):
        super().__init__(method, handler,
                         expect_handler=expect_handler,
                         resource=resource, location=location)

        self._swagger_data = {}
        self._parameters = []
        self._required = []
        self._signature = inspect.signature(handler)
        self._definitions = {}

    def set_swagger(self, swagger_data=None, definitions=None):
        if swagger_data:
            self._swagger_data = swagger_data
            parameters = self._parameters
            for param in swagger_data.get('parameters', ()):
                p = param.copy()
                if p.pop('required', False):
                    self._required.append(p['name'])
                parameters.append(p)
        if definitions:
            self._definitions = definitions

    @asyncio.coroutine
    def handler(self, request):
        parameters, missing = yield from self.validate(request)

        if missing:
            return self.rend({
                'required': missing,
            }, status=400)

        dict.update(request, parameters)

        parameters['request'] = request
        kwargs = {
            k: parameters.get(k)
            for k in self._signature.parameters
        }

        response = yield from self._handler(**kwargs)
        return response

    def _validate(self, data, schema):
        return validate(data, schema)

    @asyncio.coroutine
    def validate(self, request: web.Request):
        is_form = False
        parameters = {}
        missing = []
        if request.method not in request.POST_METHODS:
            body = None
        elif request.content_type in (
                'application/x-www-form-urlencoded',
                'multipart/form-data'):
            body = yield from request.post()
            is_form = True
        elif request.content_type == 'application/json':
            body = yield from request.json()
        else:
            body = {}

        for param in self._parameters:
            name = param['name']
            where = param['in']
            vtype = param['type']
            is_array = vtype == 'array'

            if where in ('query', 'header'):
                if where == 'query':
                    source = request.GET
                else:
                    source = request.headers
                if is_array:
                    value = source.getall(name, ())
                else:
                    value = source.get(name)
            elif where == 'path':
                value = request.match_info.get(name)
            elif not body:
                continue
            elif where == 'formData':
                if not is_form:
                    value = None
                elif is_array:
                    value = body.getall(name, ())
                else:
                    value = body.get(name)
            elif where == 'body':
                self._validate(body, param)
                parameters[name] = body
                continue
            else:
                raise ValueError(where)

            if is_array:
                vtype = param['items']['type']
            elif value is None:
                if name in self._required:
                    missing.append(name)
                continue

            conv = types_mapping[vtype]
            if vtype != 'string':
                if isinstance(value, (list, tuple)):
                    value = [conv(i) for i in value]
                else:
                    value = conv(value)

            self._validate(value, param)
            parameters[name] = value
        return parameters, missing
