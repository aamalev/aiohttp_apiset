import importlib
import inspect
import re
from itertools import islice
from typing import Any, Dict, Iterable, Optional, Tuple
from urllib.parse import urljoin

import yaml


def import_obj(path: str) -> Any:
    parts = path.rsplit('.', 1)
    if len(parts) < 2:
        raise ValueError(path)
    module_path, attribute_name = parts
    module = importlib.import_module(module_path)
    return getattr(module, attribute_name)


def normalize_url(url: str) -> str:
    """
    >>> normalize_url('//api/1/../../status')
    '/status'
    >>> normalize_url('//api/1/../../status/')
    '/status/'
    >>> normalize_url('/api/1/../../status/')
    '/status/'
    >>> normalize_url('///api/1/../../status/')
    '/status/'
    """
    u = urljoin('///{}/'.format(url), '.')
    u = re.sub(r'/+', '/', u)
    return u if url.endswith('/') else u[:-1]


def split_fqn(fqn: str) -> Tuple[str, str, str]:
    """
    >>> split_fqn('package.module.handler')
    ('package.module', '', 'handler')
    >>> split_fqn('package.module.View.handler')
    ('package.module', 'View', 'handler')
    >>> split_fqn('package.handler')
    ('package', '', 'handler')
    """
    parts = fqn.rsplit('.', 2)
    if len(parts) == 3:
        p, c, a = parts
        if c == c.lower():
            p = '.'.join((p, c))
            c = ''
    elif len(parts) == 2:
        p, a = parts
        c = ''
    else:
        raise ValueError('Unexpected FQN: {}'.format(fqn))
    return p, c, a


def pairwise(iterable: Iterable[Any]) -> Iterable[Tuple[Any, Any]]:
    a = islice(iterable, 0, None, 2)
    b = islice(iterable, 1, None, 2)
    return zip(a, b)


def load_docstring_yaml(value: str) -> Optional[Dict[str, Any]]:
    parts = value.rsplit('    ---', maxsplit=1)
    if len(parts) == 1:
        return None
    raw_data = parts[-1]
    data = yaml.load(raw_data, yaml.Loader)
    if isinstance(data, dict):
        return data
    return None


def get_unbound_method_class(obj: Any) -> Optional[Any]:
    if inspect.isfunction(obj):
        qualname = obj.__qualname__
        qualname = qualname.split('.<locals>', 1)[0]
        class_name = qualname.rsplit('.', 1)[0]
        module = inspect.getmodule(obj)
        attr = getattr(module, class_name)
        if isinstance(attr, type):
            return attr
    return None


PATTERN_RE = re.compile(r'\{(\w+):.*?\}')


def remove_patterns(url: str):
    """
    >>> remove_patterns(r'/{w:\\d+}x{h:\\d+}')
    '/{w}x{h}'
    """
    return PATTERN_RE.sub(lambda m: '{%s}' % m.group(1), url)
