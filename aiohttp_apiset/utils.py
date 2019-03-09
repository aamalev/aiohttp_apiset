import importlib
import re
from urllib import parse


def to_name(name):
    name = name.replace('/', '.')
    name = name.replace('{', '')
    name = name.replace('}', '')
    return name


def url_normolize(url: str):
    """
    >>> url_normolize('//api/1/../../status')
    '/status'
    >>> url_normolize('//api/1/../../status/')
    '/status/'
    >>> url_normolize('/api/1/../../status/')
    '/status/'
    >>> url_normolize('///api/1/../../status/')
    '/status/'
    """
    u = parse.urljoin('///{}/'.format(url), '.')
    u = re.sub(r'/+', '/', u)
    return u if url.endswith('/') else u[:-1]


re_patt = re.compile('\{(\w+):.*?\}')


def re_patt_replacer(m):
    return '{%s}' % m.group(1)


def remove_patterns(url: str):
    """
    >>> remove_patterns(r'/{w:\d+}x{h:\d+}')
    '/{w}x{h}'
    """
    return re_patt.sub(re_patt_replacer, url)


def sort_key(x):
    """
    >>> sort_key(('name', ('ROUTE', 'URL')))
    -3
    """
    name, (r, u) = x
    return - len(u) + u.count('}') * 100


def import_obj(p: str):
    r = p.rsplit('.', 1)
    if len(r) < 2:
        raise ValueError(p)
    p, c = r
    package = importlib.import_module(p)
    return getattr(package, c)


def allOf(d):
    for i in d.pop('allOf', ()):
        d.update(i)
    return d
