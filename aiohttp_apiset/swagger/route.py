import asyncio

from aiohttp import web, multidict

from ..dispatcher import Route
from .validate import convert, validate
from .loader import deref


class SwaggerRoute(Route):
    def __init__(self, method, handler, resource, *,
                 expect_handler=None, location=None, swagger_data=None):
        super().__init__(method, handler,
                         expect_handler=expect_handler,
                         resource=resource, location=location)

        self._swagger_data = swagger_data
        self._parameters = {}
        self._required = []

    def build_swagger_data(self, swagger_scheme):
        self._required = []
        self._parameters = {}
        if not self._swagger_data:
            return
        self._swagger_data = deref(self._swagger_data, swagger_scheme)
        for param in self._swagger_data.get('parameters', ()):
            p = param.copy()
            name = p.pop('name')
            self._parameters[name] = p
            if p.pop('required', False):
                self._required.append(name)

    @asyncio.coroutine
    def handler(self, request):
        parameters, errors = yield from self.validate(request)

        if errors:
            raise web.HTTPBadRequest(reason=errors)

        dict.update(request, parameters)

        parameters['request'] = request
        kwargs = {
            k: parameters.get(k)
            for k in self._handler_args
        }

        response = yield from self._handler(**kwargs)
        return response

    def _validate(self, data, errors):
        return data

    @asyncio.coroutine
    def validate(self, request: web.Request):
        is_form = False
        parameters = {}
        errors = multidict.MultiDict()

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

        for name, param in self._parameters.items():
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
                vformat = param['items'].get('format')
            elif value is None:
                if name in self._required:
                    errors.add(name, 'Required')
                continue
            else:
                vformat = param.get('format')

            value = convert(name, value, vtype, vformat, errors)

            parameters[name] = value
        self._validate(parameters, errors)
        return parameters, errors


class SwaggerValidationRoute(SwaggerRoute):
    def _validate(self, data, errors):
        return validate(data, {
            'type': 'object',
            'parameters': self._parameters,
        })


def route_factory(method, handler, resource, *,
                  expect_handler=None, **kwargs):
    if kwargs.get('swagger_data') is None:
        return Route(method, handler, resource=resource,
                     expect_handler=expect_handler)

    elif kwargs.get('validate') is True:
        route_class = SwaggerValidationRoute
    else:
        route_class = SwaggerRoute

    route = route_class(method, handler, resource=resource,
                        expect_handler=expect_handler,
                        swagger_data=kwargs['swagger_data'])
    return route
