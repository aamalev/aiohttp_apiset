import importlib
import os
import re
from pathlib import PurePath, Path
from urllib import parse


def to_name(name):
    name = name.replace('/', '.')
    name = name.replace('{', '')
    name = name.replace('}', '')
    return name


def find_file(file_path: str, search_dirs: list, *,
              base_file: str=None, base_dir: str=None) -> str:
    if isinstance(file_path, PurePath):
        if file_path.is_absolute():
            return str(file_path)

    elif file_path.startswith('/'):
        return file_path

    elif file_path.startswith('.'):
        if not base_dir and base_file:
            base_dir = os.path.dirname(base_file)
        if base_dir:
            f = os.path.join(base_dir, file_path)
            return os.path.normpath(f)

    if not isinstance(file_path, PurePath):
        file_path = PurePath(file_path)

    for base_dir in search_dirs:
        if not isinstance(base_dir, Path):
            base_dir = Path(base_dir)
        f = base_dir / file_path
        if f.exists():
            return str(f)
    raise FileNotFoundError(str(file_path))


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
    >>> remove_patterns('/{w:\d+}x{h:\d+}')
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
