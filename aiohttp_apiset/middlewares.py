import asyncio
import json

from aiohttp import web

from .utils import import_obj


DEFAULT_CONVERTERS = (
    ('multidict.MultiDict', lambda o: {k: o.getall(k) for k in o}),
    ('collections.Mapping', dict, 10),
    ('uuid.UUID', str),
    ((map, set, frozenset), list),
    ('datetime.datetime', lambda o: o.isoformat(' ')),
    ('datetime.date', lambda o: o.isoformat(), 1),
    ('decimal.Decimal', str)
)


class JsonEncoder(json.JSONEncoder):
    converters = []
    default_repr = True
    kwargs = {}

    def default(self, o):
        for score, klass, conv in self.converters:
            if isinstance(o, klass):
                return conv(o)
        if not self.default_repr:
            return super().default(o)
        try:
            return super().default(o)
        except ValueError:
            return repr(o)

    @classmethod
    def dumps(cls, *args, **kwargs):
        kwargs.setdefault('cls', cls)
        for k, v in cls.kwargs.items():
            kwargs.setdefault(k, v)
        return json.dumps(*args, **kwargs)


class Jsonify:
    encoder = JsonEncoder

    def __init__(self, *, converters=None, default_repr=True, **kwargs):
        if converters is None:
            converters = DEFAULT_CONVERTERS
        self.converters = []
        for args in converters:
            self.add_converter(*args)
        self.encoder = type(
            'Encoder', (self.encoder,),
            {
                'converters': self.converters,
                'default_repr': default_repr,
                'kwargs': kwargs,
            })

    def add_converter(self, klass, conv, score=0):
        """ Add converter
        :param klass: class or str
        :param conv: callable
        :param score:
        :return:
        """
        if isinstance(klass, str):
            klass = import_obj(klass)
        item = score, klass, conv
        self.converters.append(item)
        self.converters.sort(key=lambda x: x[0])
        return self

    def dumps(self, *args, **kwargs):
        return self.encoder.dumps(*args, **kwargs)

    @asyncio.coroutine
    def __call__(self, app, handler):
        dumps = app.get('dumps', self.dumps)

        @asyncio.coroutine
        def process(request):
            try:
                response = yield from handler(request)
            except web.HTTPException as ex:
                if not isinstance(ex.reason, str):
                    return web.json_response(
                        {'errors': ex.reason}, status=ex.status, dumps=dumps)
                elif ex.status > 399:
                    return web.json_response(
                        {'error': ex.reason}, status=ex.status, dumps=dumps)
                raise
            else:
                if isinstance(response, dict):
                    status = response.get('status', 200)
                    if not isinstance(status, int):
                        status = 200
                    return web.json_response(
                        response, status=status, dumps=dumps)
                elif not isinstance(response, web.StreamResponse):
                    return web.json_response(response, dumps=dumps)
                return response
        return process


class jsonify:
    """Class for backward compatibility"""
    singleton = None

    def __new__(cls, app, handler):
        if cls.singleton is None:
            cls.singleton = Jsonify()
        return cls.singleton(app, handler)
