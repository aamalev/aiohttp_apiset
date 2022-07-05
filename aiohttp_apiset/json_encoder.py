import json
from typing import Any, Callable, Dict, List, Tuple

from .utils import import_obj


JsonConverter = Tuple[float, Any, Callable[[Any], Any]]


DEFAULT_JSON_CONVERTERS = (
    (9.0, 'aiohttp_apiset.errors.Errors', lambda o: o.to_tree()),
    (0.0, 'multidict.MultiDict', lambda o: {k: o.getall(k) for k in o}),
    (10.0, 'collections.abc.Mapping', dict),
    (0.0, 'uuid.UUID', str),
    (0.0, (map, set, frozenset), list),
    (0.0, 'datetime.datetime', lambda o: o.isoformat(' ')),
    (1.0, 'datetime.date', lambda o: o.isoformat()),
    (0.0, 'decimal.Decimal', str)
)


class JsonEncoder(json.JSONEncoder):
    converters: List[JsonConverter] = []
    default_repr: bool = True
    kwargs: Dict[str, Any] = {}

    def default(self, o):
        for score, klass, conv in self.converters:
            if isinstance(o, klass):
                return conv(o)
        if not self.default_repr:
            return super().default(o)
        try:
            return super().default(o)
        except (ValueError, TypeError):
            return repr(o)

    @classmethod
    def dumps(cls, *args, **kwargs):
        kwargs.setdefault('cls', cls)
        for k, v in cls.kwargs.items():
            kwargs.setdefault(k, v)
        return json.dumps(*args, **kwargs)

    @classmethod
    def class_factory(cls, converters=None, default_repr=True, **kwargs):
        return type(
            'Encoder',
            (cls, ),
            {
                'converters': _process_json_converters(converters),
                'default_repr': default_repr,
                'kwargs': kwargs,
            }
        )


def _process_json_converters(converters: List[JsonConverter]):
    if converters is None:
        converters = DEFAULT_JSON_CONVERTERS

    result = []
    for item in converters:
        score, convert_from, converter = item
        if isinstance(convert_from, str):
            convert_from = import_obj(convert_from)
        result.append((score, convert_from, converter))
        result.sort(key=lambda x: x[0])
    return result
