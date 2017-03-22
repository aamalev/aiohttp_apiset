import abc
import asyncio
import inspect
import keyword
import re
import warnings
from types import MappingProxyType

from aiohttp import hdrs, HttpVersion11
from aiohttp.abc import AbstractRouter, AbstractMatchInfo, AbstractView
from aiohttp.web_exceptions import HTTPExpectationFailed

HTTP_METHOD_RE = re.compile(r"^[0-9A-Za-z!#\$%&'\*\+\-\.\^_`\|~]+$")


class AbstractRoute(abc.ABC):  # pragma: no cover

    def __init__(self, method, handler, *,
                 expect_handler=None,
                 resource=None):

        if expect_handler is None:
            expect_handler = _defaultExpectHandler

        assert asyncio.iscoroutinefunction(expect_handler), \
            'Coroutine is expected, got {!r}'.format(expect_handler)

        method = method.upper()
        if not HTTP_METHOD_RE.match(method):
            raise ValueError("{} is not allowed HTTP method".format(method))

        assert callable(handler), handler
        if asyncio.iscoroutinefunction(handler):
            pass
        elif inspect.isgeneratorfunction(handler):
            warnings.warn("Bare generators are deprecated, "
                          "use @coroutine wrapper", DeprecationWarning)
        elif (isinstance(handler, type) and
              issubclass(handler, AbstractView)):
            pass
        else:
            @asyncio.coroutine
            def handler_wrapper(*args, **kwargs):
                result = old_handler(*args, **kwargs)
                if asyncio.iscoroutine(result):
                    result = yield from result
                return result
            old_handler = handler
            handler = handler_wrapper

        self._method = method
        self._handler = handler
        self._expect_handler = expect_handler
        self._resource = resource

    @property
    def method(self):
        return self._method

    @property
    def handler(self):
        return self._handler

    @property
    @abc.abstractmethod
    def name(self):
        """Optional route's name, always equals to resource's name."""

    @property
    def resource(self):
        return self._resource

    @abc.abstractmethod
    def get_info(self):
        """Return a dict with additional info useful for introspection"""

    @abc.abstractmethod  # pragma: no branch
    def url_for(self, *args, **kwargs):
        """Construct url for route with additional params."""

    @abc.abstractmethod  # pragma: no branch
    def url(self, **kwargs):
        """Construct url for resource with additional params.

        Deprecated, use url_for() instead.

        """
        warnings.warn(".url(...) is deprecated, use .url_for instead",
                      DeprecationWarning,
                      stacklevel=3)

    @asyncio.coroutine
    def handle_expect_header(self, request):
        return (yield from self._expect_handler(request))


class UrlMappingMatchInfo(dict, AbstractMatchInfo):  # pragma: no cover

    def __init__(self, match_dict, route):
        super().__init__(match_dict)
        self._route = route
        self._apps = []
        self._frozen = False

    @property
    def handler(self):
        return self._route.handler

    @property
    def route(self):
        return self._route

    @property
    def expect_handler(self):
        return self._route.handle_expect_header

    @property
    def http_exception(self):
        return None

    def get_info(self):
        return self._route.get_info()

    @property
    def apps(self):
        return tuple(self._apps)

    def add_app(self, app):
        if self._frozen:
            raise RuntimeError("Cannot change apps stack after .freeze() call")
        self._apps.insert(0, app)

    def freeze(self):
        self._frozen = True

    def __repr__(self):
        return "<MatchInfo {}: {}>".format(super().__repr__(), self._route)


class SystemRoute(AbstractRoute):  # pragma: no cover

    def __init__(self, http_exception):
        super().__init__(hdrs.METH_ANY, self._handler)
        self._http_exception = http_exception

    def url_for(self, *args, **kwargs):
        raise RuntimeError(".url_for() is not allowed for SystemRoute")

    def url(self, *args, **kwargs):
        raise RuntimeError(".url() is not allowed for SystemRoute")

    @property
    def name(self):
        return None

    def get_info(self):
        return {'http_exception': self._http_exception}

    @asyncio.coroutine
    def _handler(self, request):
        raise self._http_exception

    @property
    def status(self):
        return self._http_exception.status

    @property
    def reason(self):
        return self._http_exception.reason

    def __repr__(self):
        return "<SystemRoute {self.status}: {self.reason}>".format(self=self)


class MatchInfoError(UrlMappingMatchInfo):  # pragma: no cover

    def __init__(self, http_exception):
        self._exception = http_exception
        super().__init__({}, SystemRoute(self._exception))

    @property
    def http_exception(self):
        return self._exception

    def __repr__(self):
        return "<MatchInfoError {}: {}>".format(self._exception.status,
                                                self._exception.reason)


@asyncio.coroutine
def _defaultExpectHandler(request):  # pragma: no cover
    """Default handler for Expect header.

    Just send "100 Continue" to client.
    raise HTTPExpectationFailed if value of header is not "100-continue"
    """
    expect = request.headers.get(hdrs.EXPECT)
    if request.version == HttpVersion11:
        if expect.lower() == "100-continue":
            request.transport.write(b"HTTP/1.1 100 Continue\r\n\r\n")
        else:
            raise HTTPExpectationFailed(text="Unknown Expect: %s" % expect)


class CompatRouter(AbstractRouter):
    DYN = re.compile(r'\{(?P<var>[_a-zA-Z][_a-zA-Z0-9]*)\}')
    DYN_WITH_RE = re.compile(
        r'\{(?P<var>[_a-zA-Z][_a-zA-Z0-9]*):(?P<re>.+)\}')
    GOOD = r'[^{}/]+'
    ROUTE_RE = re.compile(r'(\{[_a-zA-Z][^{}]*(?:\{[^{}]*\}[^{}]*)*\})')
    NAME_SPLIT_RE = re.compile(r'[.:-]')

    def __init__(self):
        super().__init__()
        self._app = None
        self._named_resources = {}

    def __iter__(self):
        return iter(self._named_resources)

    def __len__(self):
        return len(self._named_resources)

    def __contains__(self, name):
        return name in self._named_resources

    def __getitem__(self, name):
        return self._named_resources[name]

    def named_resources(self):
        return MappingProxyType(self._named_resources)

    def post_init(self, app):
        assert app is not None
        self._app = app

    def validate_name(self, name: str):
        """
        Fragment aiohttp.web_urldispatcher.UrlDispatcher#_reg_resource
        """
        parts = self.NAME_SPLIT_RE.split(name)
        for part in parts:
            if not part.isidentifier() or keyword.iskeyword(part):
                raise ValueError('Incorrect route name {!r}, '
                                 'the name should be a sequence of '
                                 'python identifiers separated '
                                 'by dash, dot or column'.format(name))
        if name in self._named_resources:
            raise ValueError('Duplicate {!r}, '
                             'already handled by {!r}'
                             .format(name, self._named_resources[name]))

    @classmethod
    def get_pattern_formatter(cls, location):
        """
        Fragment from aiohttp.web_urldispatcher.UrlDispatcher#add_resource
        :param location:
        :return:
        """
        pattern = ''
        formatter = ''
        canon = ''
        for part in cls.ROUTE_RE.split(location):
            match = cls.DYN.match(part)
            if match:
                pattern += '(?P<{}>{})'.format(match.group('var'), cls.GOOD)
                formatter += '{' + match.group('var') + '}'
                continue

            match = cls.DYN_WITH_RE.match(part)
            if match:
                pattern += '(?P<{var}>{re})'.format(**match.groupdict())
                formatter += '{' + match.group('var') + '}'
                canon += match.group('re')
                continue

            if '{' in part or '}' in part:
                raise ValueError("Invalid path '{}'['{}']".format(
                    location, part))

            formatter += part
            pattern += re.escape(part)
            canon += part

        try:
            return re.compile(pattern), formatter, canon
        except re.error as exc:
            raise ValueError(
                "Bad pattern '{}': {}".format(pattern, exc)) from None

    def add_head(self, *args, **kwargs):
        """
        Shortcut for add_route with method HEAD
        """
        return self.add_route(hdrs.METH_HEAD, *args, **kwargs)

    def add_get(self, *args, **kwargs):
        """
        Shortcut for add_route with method GET
        """
        return self.add_route(hdrs.METH_GET, *args, **kwargs)

    def add_post(self, *args, **kwargs):
        """
        Shortcut for add_route with method POST
        """
        return self.add_route(hdrs.METH_POST, *args, **kwargs)

    def add_put(self, *args, **kwargs):
        """
        Shortcut for add_route with method PUT
        """
        return self.add_route(hdrs.METH_PUT, *args, **kwargs)

    def add_patch(self, *args, **kwargs):
        """
        Shortcut for add_route with method PATCH
        """
        return self.add_route(hdrs.METH_PATCH, *args, **kwargs)

    def add_delete(self, *args, **kwargs):
        """
        Shortcut for add_route with method DELETE
        """
        return self.add_route(hdrs.METH_DELETE, *args, **kwargs)
