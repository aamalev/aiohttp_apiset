import functools
import json
import sys

from .swagger.loader import SwaggerLoaderMixin
from . import utils

PY_35 = sys.version_info >= (3, 5)


class BaseApiSet:
    pass


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
