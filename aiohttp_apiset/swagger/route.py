import asyncio
from collections.abc import Mapping

from aiohttp import web

from aiohttp_apiset.exceptions import ValidationError
from .operations import get_docstring_swagger
from .validate import convert, Validator, get_collection
from ..dispatcher import Route


class SwaggerRoute(Route):
    """
    :param method: as well as in aiohttp
    :param handler: as well as in aiohttp
    :param resource: as well as in aiohttp
    :param expect_handler: as well as in aiohttp
    :param location: SubLocation instance
    :param swagger_data: data
    """
    errors_factory = ValidationError

    def __init__(self, method, handler, resource, *,
                 expect_handler=None, location=None,
                 swagger_data=None, build=True):
        super().__init__(method, handler,
                         expect_handler=expect_handler,
                         resource=resource, location=location)
        self._parameters = {}
        self._required = []
        self._swagger_data = swagger_data
        self.is_built = False
        if build:
            self.build_swagger_data()

    @property
    def swagger_operation(self):
        return self._swagger_data

    def build_swagger_data(self):
        """ Prepare data when schema loaded

        :param swagger_schema: loaded schema
        """
        if self.is_built:
            return
        self.is_built = True
        self._required = []
        self._parameters = {}
        if not self._swagger_data:
            return

        def allOf(d):
            for i in d.pop('allOf', ()):
                d.update(i)
            return d

        for param in self._swagger_data.get('parameters', ()):
            p = allOf(param.copy())
            name = p.pop('name')
            self._parameters[name] = p
            if p.pop('required', False):
                self._required.append(name)
            if 'schema' in p:
                p.update(allOf(p.pop('schema')))

    @asyncio.coroutine
    def handler(self, request):
        parameters, errors = yield from self.validate(request)
        ha = self._handler_args
        kw = self._handler_kwargs

        if errors and 'errors' not in ha:
            raise errors

        request.update(parameters)
        if 'errors' in ha:
            parameters['errors'] = errors
        if 'request' in ha:
            parameters['request'] = request

        if kw:
            parameters, ps = parameters, parameters
        else:
            parameters, ps = {}, parameters
        for k, p in ha.items():
            if k in parameters:
                continue
            elif k in ps:
                parameters[k] = ps[k]
            elif p and p.default == p.empty:
                parameters[k] = None

        response = yield from self._handler(**parameters)
        return response

    def _validate(self, data, errors):
        return data

    @asyncio.coroutine
    def validate(self, request: web.Request):
        """ Returns parameters extract from request and multidict errors

        :param request: Request
        :return: tuple of parameters and errors
        """
        parameters = {}
        files = {}
        errors = self.errors_factory()
        body = None

        if request.method not in request.POST_METHODS:
            pass
        elif request.content_type in (
                'application/x-www-form-urlencoded',
                'multipart/form-data'):
            try:
                body = yield from request.post()
            except ValueError as e:
                errors[request.content_type].add(str(e))
            except Exception:
                errors[request.content_type].add('Bad form')
        elif request.content_type == 'application/json':
            try:
                body = yield from request.json()
            except ValueError as e:
                errors[request.content_type].add(str(e))
            except Exception:
                errors[request.content_type].add('Bad json')
        elif request.content_type == 'application/octet-stream':
            body = yield from request.read()
            if not len(body):
                body = None
        elif request.content_type:
            errors[request.content_type].add('Not supported content type')

        for name, param in self._parameters.items():
            where = param['in']
            vtype = param['type']
            is_array = vtype == 'array'

            if where == 'query':
                source = request.query
            elif where == 'header':
                source = request.headers
            elif where == 'path':
                source = request.match_info
            elif body is None:
                source = ()
            elif where == 'formData':
                source = body
            elif where == 'body':
                if isinstance(body, BaseException):
                    errors[name].add(str(body))
                else:
                    parameters[name] = body
                continue
            else:
                raise ValueError(where)

            if is_array and hasattr(source, 'getall'):
                collection_format = param.get('collectionFormat')
                default = param.get('default', [])
                value = get_collection(source, name,
                                       collection_format, default)
                if param.get('minItems') and not value \
                        and name not in self._required:
                    continue
            elif isinstance(source, Mapping) and name in source \
                    and (vtype not in ('number', 'integer') or
                         source[name] != ''):
                value = source[name]
            elif 'default' in param:
                parameters[name] = param['default']
                continue
            elif name in self._required:
                errors[name].add('Required')
                if isinstance(source, BaseException):
                    errors[name].add(str(body))
                continue
            else:
                continue

            if is_array:
                vtype = param['items']['type']
                vformat = param['items'].get('format')
            else:
                vformat = param.get('format')

            if source is body and isinstance(body, dict):
                pass
            elif vtype not in ('string', 'file'):
                value = convert(name, value, vtype, vformat, errors)

            if vtype == 'file':
                files[name] = value
            else:
                parameters[name] = value

        parameters = self._validate(parameters, errors)
        parameters.update(files)
        return parameters, errors


class SwaggerValidationRoute(SwaggerRoute):
    def build_swagger_data(self):
        if self.is_built:
            return
        super().build_swagger_data()
        schema = {
            'type': 'object',
            'properties': self._parameters,
        }
        self._validator = Validator(schema)

    def _validate(self, data, errors):
        return self._validator.validate(data, errors)


def route_factory(method, handler, resource, *,
                  expect_handler=None, **kwargs):

    ds_swagger_op = get_docstring_swagger(handler)
    if ds_swagger_op:
        swagger_data = ds_swagger_op
    else:
        swagger_data = kwargs.get('swagger_data')

    if swagger_data is None:
        return Route(method, handler, resource=resource,
                     expect_handler=expect_handler)

    elif kwargs.get('validate') is True:
        route_class = SwaggerValidationRoute
    else:
        route_class = SwaggerRoute

    route = route_class(method, handler, resource=resource,
                        expect_handler=expect_handler,
                        swagger_data=swagger_data)
    if ds_swagger_op:
        route.build_swagger_data()
    return route
