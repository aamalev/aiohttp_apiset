import asyncio
import importlib
import inspect
import mimetypes
import re
from collections.abc import Container, Iterable, Mapping, Sized
from itertools import chain
from urllib import parse
from pathlib import Path

import yarl
from aiohttp import hdrs
from aiohttp.abc import AbstractView
from aiohttp.web_exceptions import \
    HTTPMethodNotAllowed, HTTPNotFound, HTTPForbidden
from aiohttp.web import Response

from .compat import (
    CompatRouter, AbstractRoute, UrlMappingMatchInfo, MatchInfoError,
)


class SubLocation:
    SPLIT = re.compile(r'/((?:(?:\{.+?\})|(?:[^/{}]+))+)')

    def __init__(self, *, formatter, name='', canon=None, parent=None,
                 resource=None):
        self._name = name
        self._formatter = formatter
        self._canon = canon
        self._parent = parent
        self._subs = {}
        self._patterns = []
        self._routes = {}
        self._resource = resource

    @property
    def name(self):
        return self._name

    @property
    def canon(self):
        return self._canon

    @property
    def formatter(self):
        parts = []
        parent = self._parent
        while parent is not None:
            parts.append(parent._formatter)
            parent = parent._parent
        if parts:
            parts.reverse()
            parts.append(self._formatter)
            url = '/'.join(parts)
        else:
            url = '/'
        return url

    def url(self, *, parts=None, query=None, **kwargs):
        url = self.formatter
        parts = parts or kwargs
        if parts:
            url = url.format_map(parts)
        if query:
            url += "?" + parse.urlencode(query)
        return url

    def url_for(self, *args, **kwargs):
        """Construct url for route with additional params."""
        return yarl.URL(self.url(parts=kwargs))

    def get_info(self):
        url = self.formatter
        if '{' in url:
            return {'formatter': url}
        else:
            return {'path': url}

    def __repr__(self):
        return '<SubLocation {name}, url={url}>' \
               ''.format(name=self.name, url=self.url())

    @classmethod
    def split(cls, path):
        locations = [i for i in cls.SPLIT.split(path) if i]
        if locations[-1] == '/':
            locations[-1] = ''
        return locations

    def resolve(self, request, path: str, match_dict: dict):
        method = request.method
        allowed_methods = set()

        if path is None:
            allowed_methods.update(self._routes)
            if method in self._routes:
                route = self._routes[method]
            elif hdrs.METH_ANY in self._routes:
                route = self._routes[hdrs.METH_ANY]
            else:
                return None, allowed_methods
            return UrlMappingMatchInfo(match_dict, route), allowed_methods
        elif not path:
            location = path
            tail = None
        else:
            parts = path.split('/', 1)
            if len(parts) == 2:
                location, tail = parts
            else:
                location = parts[0]
                tail = None

        if location in self._subs:
            return self._subs[location].resolve(
                request=request,
                path=tail,
                match_dict=match_dict)

        for pattern, sublocation in self._patterns:
            m = pattern.match(path)
            if m is not None:
                for key, value in m.groupdict().items():
                    match_dict[key] = parse.unquote(value)

                index = m.end()
                if len(path) > index:
                    if path[index] == '/':
                        index += 1
                    tail = path[index:]
                else:
                    tail = None

                return sublocation.resolve(
                    request=request, path=tail, match_dict=match_dict)
        return None, allowed_methods

    def register_route(self, path, route, resource=None, name=None):
        if not path:
            assert route.method not in self._routes, self
            self._routes[route.method] = route
            return self
        location = self.add_location(path, resource, name)
        return location.register_route(None, route)

    def add_location(self, path, resource=None, name=None):
        if resource is None:
            resource = self._resource

        if isinstance(path, str):
            path = self.split(path)
        if not path:
            if name:
                self._name = name
            return self

        location_name, *path = path

        if '{' in location_name:
            pattern, formatter, canon = \
                TreeUrlDispatcher.get_pattern_formatter(location_name)
            for ptrn, loc in self._patterns:
                if loc._canon == canon:
                    if loc._formatter != formatter:
                        raise ValueError(
                            'Similar patterns "{}" and "{}" for location {}'
                            ''.format(loc.name, location_name,
                                      loc.url_for().human_repr()))
                    location = loc
                    break
            else:
                cls = type(self)
                location = cls(
                    formatter=formatter, canon=canon,
                    parent=self, resource=resource)
                self._patterns.append((pattern, location))
        elif location_name in self._subs:
            location = self._subs[location_name]
        else:
            location = type(self)(
                formatter=location_name, parent=self, resource=resource)
            self._subs[location_name] = location

        return location.add_location(path, resource=resource, name=name)

    def add_route(self, method, handler, *,
                  expect_handler=None, **kwargs):
        route = self._resource._route_factory(
            method, handler, self._resource,
            expect_handler=expect_handler, **kwargs)
        route.location = self.register_route(None, route)
        return route


class Route(AbstractRoute):
    def __init__(self, method, handler, resource, *,
                 expect_handler=None, location=None, **kwargs):
        handler, self._handler_args = self._wrap_handler(handler)
        super().__init__(method, handler,
                         expect_handler=expect_handler,
                         resource=resource)
        self._location = location
        self._extra_info = {}

    def __repr__(self):
        return type(self).__name__

    @property
    def name(self):
        return self._location.name

    def url_for(self, *args, **kwargs):
        """Construct url for route with additional params."""
        return self._location.url_for(*args, **kwargs)

    def url(self, **kwargs):
        """Construct url for route with additional params."""
        return self._location.url(**kwargs)

    def get_info(self):
        result = self._location.get_info()
        result.update(self._extra_info)
        return result

    def set_info(self, **kwargs):
        self._extra_info.update(kwargs)

    @property
    def location(self):
        return self._location

    @location.setter
    def location(self, value):
        self._location = value

    @classmethod
    def _wrap_handler(cls, handler):
        if isinstance(handler, str):
            return cls._import_handler(handler)
        signature = inspect.signature(handler)
        handler_kwargs = frozenset(signature.parameters.keys())
        return handler, handler_kwargs

    @classmethod
    def _import_handler(cls, path: str):
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
            return cls._wrap_handler(getattr(package, h))

        View = getattr(package, v)

        if issubclass(View, AbstractView):
            return cls._wrap_handler(View)

        handler = getattr(View, h)
        signature = inspect.signature(getattr(View(), h))
        handler_kwargs = frozenset(signature.parameters.keys())
        if 'request' in handler_kwargs:
            def wrap_handler(request, *args, **kwargs):
                vi = View()
                vi.request = request
                return handler(vi, request, *args, **kwargs)
        else:
            def wrap_handler(request, *args, **kwargs):
                vi = View()
                vi.request = request
                return handler(vi, *args, **kwargs)

        wrap_handler.__signature__ = signature
        return wrap_handler, {'request'}.union(handler_kwargs)


class TreeResource:
    def __init__(self, *, name=None,
                 route_factory=None,
                 sublocation_factory=None):
        self._routes = []
        self._route_factory = route_factory or Route
        self._sublocation_factory = sublocation_factory or SubLocation
        self._location = self._sublocation_factory(formatter='', resource=self)
        self._name = name

    @property
    def name(self):
        return self._name

    def add_route(self, method, handler, *,
                  path='/', expect_handler=None, name=None, **kwargs):
        path = self._location.split(path)
        route = self._route_factory(method, handler, self,
                                    expect_handler=expect_handler, **kwargs)
        location = self._location.register_route(
            path, route, resource=self, name=name)
        route.location = location
        return route

    @asyncio.coroutine
    def resolve(self, request):
        path = getattr(request, 'rel_url', request).raw_path
        return self._location.resolve(request, path[1:], {})

    def get_info(self):
        return {}

    def url_for(self, *args, **kwargs):
        """Construct url for route with additional params."""
        return self._location.url_for(*args, **kwargs)

    def url(self, *, parts=None, query=None):
        return self._location.url(parts=parts, query=query)

    def __repr__(self):
        name = "'" + self.name + "' " if self.name is not None else ""
        return "<TreeResource {name}>".format(name=name)

    def __len__(self):
        return len(self._routes)

    def __iter__(self):
        return iter(self._routes)


class ResourcesView(Sized, Iterable, Container):

    def __init__(self, resource: TreeResource):
        location = resource._location
        self._resources = self._append(location, [location])

    def _append(self, location: SubLocation, acc):
        ptrns = (l for p, l in location._patterns)
        for i in chain(location._subs.values(), ptrns):
            acc.append(i)
            self._append(i, acc)
        return acc

    def __len__(self):
        return len(self._resources)

    def __iter__(self):
        yield from self._resources

    def __contains__(self, resource):
        return resource in self._resources


class RoutesView(Sized, Iterable, Container):

    def __init__(self, resource: TreeResource):
        location = resource._location
        self._routes = self._append(location, [])

    def _append(self, location: SubLocation, acc):
        ptrns = (l for p, l in location._patterns)
        for i in chain(location._subs.values(), ptrns):
            acc.extend(i._routes.values())
            self._append(i, acc)
        return acc

    def __len__(self):
        return len(self._routes)

    def __iter__(self):
        yield from self._routes

    def __contains__(self, route):
        return route in self._routes


class TreeUrlDispatcher(CompatRouter, Mapping):
    def __init__(self, *,
                 resource_factory=TreeResource,
                 route_factory=Route):
        super().__init__()
        self._resource = resource_factory(route_factory=route_factory)
        self._executor = None

    @asyncio.coroutine
    def resolve(self, request):
        match, allowed = yield from self._resource.resolve(request)

        if match is not None:
            return match
        elif allowed:
            return MatchInfoError(
                HTTPMethodNotAllowed(request.method, allowed))
        else:
            return MatchInfoError(HTTPNotFound())

    def resources(self):
        return ResourcesView(self._resource)

    def routes(self):
        return RoutesView(self._resource)

    @property
    def tree_resource(self) -> TreeResource:
        return self._resource

    def add_route(self, method, path, handler,
                  *, name=None, expect_handler=None, **kwargs):
        if path and not path.startswith('/'):
            raise ValueError("path should be started with / or be empty")
        if name:
            self.validate_name(name)

        route = self.tree_resource.add_route(
            method=method, handler=handler,
            path=path, expect_handler=expect_handler,
            name=name, **kwargs)

        if name:
            self._named_resources[name] = route.location
        return route

    def add_resource(self, path, *, name=None):
        if path and not path.startswith('/'):
            raise ValueError("path should be started with / or be empty")
        if name:
            self.validate_name(name)

        location = self._resource._location.add_location(
            path, resource=self._resource, name=name)

        if name:
            self._named_resources[name] = location

        return location

    def add_static(self, prefix, path, *, name=None, default=None):
        from concurrent.futures import ThreadPoolExecutor

        if not prefix.endswith('/'):
            prefix += '/'

        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=1)

        if isinstance(path, str):
            path = Path(path)

        def search(filename, default):
            p = path / filename
            if filename and p.exists():
                return p
            elif default:
                if filename:
                    d = p.parent
                else:
                    d = p
            else:
                return
            while True:
                p = d / default
                if p.exists():
                    return p
                if d <= path:
                    return
                d = d.parent

        def read_bytes(p):
            with p.open('br') as f:
                return f.read()

        @asyncio.coroutine
        def content(request):
            filename = request.match_info['filename']

            if filename:
                if '..' in filename:
                    raise HTTPForbidden()
            elif not isinstance(default, str):
                raise HTTPNotFound()
            f = yield from request.app.loop.run_in_executor(
                self._executor, search, filename, default)

            if not f:
                raise HTTPNotFound()

            ct, encoding = mimetypes.guess_type(f.name)
            if not ct:
                ct = 'application/octet-stream'
            body = yield from request.app.loop.run_in_executor(
                self._executor, read_bytes, f)
            return Response(body=body, content_type=ct)

        route = self.add_route('GET', prefix + '{filename:.*}',
                               content, name=name)
        route.set_info(prefix=prefix, directory=str(path), default=default)
