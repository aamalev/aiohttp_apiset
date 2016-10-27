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
        self._json_form = False

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
        parameters = {}
        files = {}
        errors = multidict.MultiDict()

        if request.method not in request.POST_METHODS:
            body = None
        elif request.content_type in (
                'application/x-www-form-urlencoded',
                'multipart/form-data'):
            body = yield from request.post()
        elif request.content_type == 'application/json':
            body = yield from request.json()
        else:
            body = None

        for name, param in self._parameters.items():
            where = param['in']
            vtype = param['type']
            is_array = vtype == 'array'

            if where == 'query':
                source = request.GET
            elif where == 'header':
                source = request.headers
            elif where == 'path':
                source = request.match_info
            elif body is None:
                source = ()
            elif where == 'formData':
                source = body
            elif where == 'body':
                parameters[name] = body
                continue
            else:
                raise ValueError(where)

            if is_array and hasattr(source, 'getall'):
                value = source.getall(name, ())
            elif name in source:
                value = source[name]
            elif name in self._required:
                errors.add(name, 'Required')
                continue
            else:
                continue

            if is_array:
                vtype = param['items']['type']
                vformat = param['items'].get('format')
            else:
                vformat = param.get('format')

            if not isinstance(source, dict) \
                    and vtype not in ('string', 'file'):
                value = convert(name, value, vtype, vformat, errors)

            if vtype == 'file':
                files[name] = value
            else:
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
